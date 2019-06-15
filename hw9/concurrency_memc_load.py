import threading
import multiprocessing
import queue
import memcache
import time
import os
import gzip
import sys
import glob
import logging
import collections
import appsinstalled_pb2
from optparse import OptionParser
from functools import partial
from timer import timer

NORMAL_ERR_RATE = 0.01
AppsInstalled = collections.namedtuple("AppsInstalled", ["dev_type", "dev_id", "lat", "lon", "apps"])
Serialized_data = collections.namedtuple('Serialized_data', 'data key packed_data')

NUM_RECONNECT_MEMC = 3
TIMEOUT_MEMC = 1
WAIT_FACTOR = 0.1
QUEUE_TIMEOUT = 1


def dot_rename(path):
    head, fn = os.path.split(path)
    # atomic in most cases
    os.rename(path, os.path.join(head, "." + fn))


def serialization_data(appsinstalled):
    ua = appsinstalled_pb2.UserApps()
    ua.lat = appsinstalled.lat
    ua.lon = appsinstalled.lon
    key = "%s:%s" % (appsinstalled.dev_type, appsinstalled.dev_id)
    ua.apps.extend(appsinstalled.apps)
    packed = ua.SerializeToString()
    return Serialized_data(ua, key, packed)


def insert_appsinstalled(memc_connect, values_for_insert):
    list_of_fails = [1] * 100
    for i in range(NUM_RECONNECT_MEMC):
        list_of_fails = memc_connect.set_multi(values_for_insert)
        if len(list_of_fails) == 0:
            break
        time.sleep(WAIT_FACTOR * ((i + 1) ** i))
        values_for_insert = {key: values_for_insert[key] for key in list_of_fails}
    dict_not_insert = {key: values_for_insert[key] for key in list_of_fails}
    return dict_not_insert


def parse_appsinstalled(line):
    line = line.decode()
    line_parts = line.strip().split("\t")
    if len(line_parts) < 5:
        return
    dev_type, dev_id, lat, lon, raw_apps = line_parts
    if not dev_type or not dev_id:
        return
    try:
        apps = [int(a.strip()) for a in raw_apps.split(",")]
    except ValueError:
        apps = [int(a.strip()) for a in raw_apps.split(",") if a.isidigit()]
        logging.info("Not all user apps are digits: `%s`" % line)
    try:
        lat, lon = float(lat), float(lon)
    except ValueError:
        logging.info("Invalid geo coords: `%s`" % line)
    return AppsInstalled(dev_type, dev_id, lat, lon, apps)


def insert_handler(memc_addr, insert_queue, result_queue):
    tprocessed = terrors = 0
    memc_connect = memcache.Client([memc_addr], socket_timeout=TIMEOUT_MEMC)
    values_for_insert = {}
    while True:
        try:
            serialized_data = insert_queue.get(timeout=QUEUE_TIMEOUT)
            values_for_insert[serialized_data.key] = serialized_data.packed_data
            if len(values_for_insert) == 500:
                result = insert_appsinstalled(memc_connect, values_for_insert)
                values_for_insert = {}
            else:
                continue
        except queue.Empty:
            if not values_for_insert:
                break
            result = insert_appsinstalled(memc_connect, values_for_insert)
            values_for_insert = {}
        if result:
            tprocessed += 100 - len(result)
            terrors += len(result)
            logging.error("Cannot write to memc %s, %s strings" % (memc_addr, len(result)))
        else:
            tprocessed += 100
    result_queue.put((tprocessed, terrors))


def file_handler(fn, options):
    device_memc = {
        "idfa": options.idfa,
        "gaid": options.gaid,
        "adid": options.adid,
        "dvid": options.dvid,
    }

    insert_queues = {
        "idfa": queue.Queue(),
        "gaid": queue.Queue(),
        "adid": queue.Queue(),
        "dvid": queue.Queue(),
    }

    result_queue = queue.Queue()

    threads = []
    for key in device_memc:
        t = threading.Thread(target=insert_handler, args=(device_memc[key], insert_queues[key], result_queue))
        t.daemon = True
        threads.append(t)
    for t in threads:
        t.start()

    processed = errors = 0
    logging.info('Processing %s' % fn)
    with gzip.open(fn) as fd:
        for line in fd:
            line = line.strip()
            if not line:
                continue
            appsinstalled = parse_appsinstalled(line)
            if not appsinstalled:
                errors += 1
                continue
            memc_addr = device_memc.get(appsinstalled.dev_type)
            if not memc_addr:
                errors += 1
                logging.error("Unknow device type: %s" % appsinstalled.dev_type)
                continue
            serialized_data = serialization_data(appsinstalled)
            if options.dry:
                logging.debug("%s - %s -> %s" %
                              (memc_addr, serialized_data.key, str(serialized_data.data).replace("\n", " ")))
            else:
                insert_queues[appsinstalled.dev_type].put(serialized_data)

    for thread in threads:
        if thread.is_alive():
            thread.join()

    while True:
        try:
            tprocessed, terrors = result_queue.get(timeout=QUEUE_TIMEOUT)
        except queue.Empty:
            break
        processed += tprocessed
        errors += terrors

    if processed:
        err_rate = float(errors) / processed
        if err_rate < NORMAL_ERR_RATE:
            logging.info("Acceptable error rate (%s). Successfull load" % err_rate)
        else:
            logging.error("High error rate (%s > %s). Failed load" % (err_rate, NORMAL_ERR_RATE))
    return fn


@timer
def main(options):
    fn_list = list(glob.iglob(options.pattern))
    fn_list.sort()
    num_proc = multiprocessing.cpu_count()
    processes_pool = multiprocessing.Pool(processes=num_proc)
    file_handler_options = partial(file_handler, options=options)
    for fn in processes_pool.imap(file_handler_options, fn_list):
        dot_rename(fn)


def prototest():
    sample = "idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23\ngaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424"
    for line in sample.splitlines():
        dev_type, dev_id, lat, lon, raw_apps = line.strip().split("\t")
        apps = [int(a) for a in raw_apps.split(",") if a.isdigit()]
        lat, lon = float(lat), float(lon)
        ua = appsinstalled_pb2.UserApps()
        ua.lat = lat
        ua.lon = lon
        ua.apps.extend(apps)
        packed = ua.SerializeToString()
        unpacked = appsinstalled_pb2.UserApps()
        unpacked.ParseFromString(packed)
        assert ua == unpacked


if __name__ == '__main__':
    op = OptionParser()
    op.add_option("-t", "--test", action="store_true", default=False)
    op.add_option("-l", "--log", action="store", default=None)
    op.add_option("--dry", action="store_true", default=False)
    op.add_option("--pattern", action="store", default="data/appsinstalled/*.tsv.gz")
    op.add_option("--idfa", action="store", default="127.0.0.1:33013")
    op.add_option("--gaid", action="store", default="127.0.0.1:33014")
    op.add_option("--adid", action="store", default="127.0.0.1:33015")
    op.add_option("--dvid", action="store", default="127.0.0.1:33016")
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO if not opts.dry else logging.DEBUG,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    if opts.test:
        prototest()
        sys.exit(0)

    logging.info("Memc loader started with options: %s" % opts)
    try:
        main(opts)
    except Exception as e:
        logging.exception("Unexpected error: %s" % e)
        sys.exit(1)
