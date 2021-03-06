# !/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';
# sys.argv -> ['file_name.py', 'dir_log_nginx', 'config']

import re
import gzip
import json
import argparse
import configparser
import logging
import os
from datetime import datetime
from collections import namedtuple, defaultdict
from string import Template
from fractions import Fraction


config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log",
    "LEVEL_PARSE": 50,
    "LOGGING_LEVEL": logging.DEBUG,
    "LOGGING_TO_FILE": None
}
Log = namedtuple('log', 'file_for_analyze date ex')
Req = namedtuple('req', 'url time')


def create_parser():
    default = "{}/config_log_analyzer".format(os.path.dirname(os.path.abspath(__file__)))
    parser_ = argparse.ArgumentParser()
    parser_.add_argument('-c', '--config', default=default)
    return parser_


def parse_config(default_config, path):
    priority_config = configparser.ConfigParser()
    priority_config.read(path)
    if priority_config.sections():
        priority_config = dict(priority_config.items('Config_log_analyzer'))
        for item in priority_config.items():
            if item[1] == 'DEBUG':
                priority_config[item[0]] = logging.DEBUG
            if item[1] == 'INFO':
                priority_config[item[0]] = logging.INFO
            if item[1] == 'ERROR':
                priority_config[item[0]] = logging.ERROR
            if item[1].isdigit():
                priority_config[item[0]] = int(item[1])
            default_config[item[0].upper()] = priority_config[item[0]]
    return default_config


def find_log(dir_log_nginx):
    maximum = None
    file_for_analyze = None
    date = 0
    ex = None
    if not os.path.exists(dir_log_nginx):
        raise Exception('{} no such directory!'.format(dir_log_nginx))
    for file_ in os.listdir(dir_log_nginx):
        f = re.match(r'nginx-access-ui.log-(?P<cur_date>\d{8})(\.(?P<cur_ex>gz)|$)', file_)
        if not f or not os.path.isfile(os.path.join(dir_log_nginx, file_)):
            continue
        try:
            cur_date, cur_ex = datetime.strptime(f.group('cur_date'), '%Y%m%d'), f.group('cur_ex')
        except ValueError:
            continue
            # raise ValueError('Invalid date in file_log -> {}'.format(file_))
        maximum = (max(maximum, cur_date) if maximum is not None else cur_date)
        if cur_date == maximum:
            file_for_analyze = file_
            date, ex = cur_date, cur_ex
    return Log(file_for_analyze, date, ex) if file_for_analyze else None


def parse_string(file_from):
    for line in file_from:
        line = line.decode('utf-8')
        lst = line.split()
        pattern_ip = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
        pattern_url = r'(/\w*)+'
        pattern_time = r'\d+(\.\d+)'
        try:
            if re.match(pattern_ip, lst[0]) and re.match(pattern_url, lst[6]) and re.match(pattern_time, lst[-1]):
                url, time = lst[6], float(lst[-1])
                yield Req(url, time)
            else:
                yield None
        except IndexError:
            yield None


def parse_log(path_file_for_analyze, ex):
    file_open = open if ex is None else gzip.open
    data = defaultdict(list)
    all_time = 0
    all_strings = 0
    good_strings = 0
    with file_open(path_file_for_analyze, 'r') as log_file:
        for string_log in parse_string(log_file):
            all_strings += 1
            if string_log is not None:
                good_strings += 1
                all_time += string_log.time
                key = string_log.url
                data[key].append(string_log.time)
    persent = 0
    if all_strings > 0:
        persent = Fraction(good_strings, all_strings)
    return data, good_strings, all_time, persent


def count_stat(data,  num_req, all_time, report_size=5):  # data ->{url: [list_of_times]},
    data_to_render_ = []                                  # report_size -> config["REPORT_SIZE"]
    for key in data:
        time_sum = round(sum(data[key]), 3)
        data[key] = (time_sum, data[key])
    sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)
    i = 0
    ceiling = min(report_size, len(sorted_data))
    while i < ceiling:
        time_sum = sorted_data[i][1][0]
        list_of_times = sorted_data[i][1][1]
        list_of_times.sort()
        count = len(list_of_times)
        count_perc = round(count / (num_req * 1.0) * 100, 3)
        time_perc = round(time_sum / (all_time * 1.0) * 100, 3)
        time_avg = round(time_sum / (count * 1.0), 3)
        if count % 2 == 1:
            time_med = list_of_times[count / 2]
        else:
            time_med = list_of_times[count / 2 - 1]
        data_to_render_.append({
            'url': sorted_data[i][0],
            'count': count,
            'count_perc': count_perc,
            'time_avg': time_avg,
            'time_max': list_of_times[-1],
            'time_med': time_med,
            'time_perc': time_perc,
            'time_sum': time_sum
        })
        i += 1
    return data_to_render_


def render_report(data_to_render_, report_path):
    table_json = json.dumps(data_to_render_, indent=4)
    with open('report.html', 'r') as report:
        report = report.read().decode('utf-8')
        report_to_file = Template(report)
    report_to_file = report_to_file.safe_substitute(table_json=table_json)
    with open(report_path, 'w') as report_date:
        report_to_file = report_to_file.encode('utf-8')
        report_date.write(report_to_file)


def check_report(path, conf):
    if os.path.exists(conf['REPORT_DIR']):
        if os.path.exists(path):
            return True
    else:
        os.makedirs(conf['REPORT_DIR'])
    return False


def main(conf):
    logging.basicConfig(format='[%(asctime)s] %(levelname).1s %(message)s', level=conf["LOGGING_LEVEL"],
                        filename=conf["LOGGING_TO_FILE"])

    file_log = find_log(conf["LOG_DIR"])
    if file_log is None:
        logging.error('File_for_analyze is not found.')
        return
    logging.debug("find_log: {} OK".format(file_log.file_for_analyze))

    report_path = os.path.join(conf['REPORT_DIR'], 'report-{}.html'.format(file_log.date.strftime('%Y.%m.%d')))
    if check_report(report_path, conf):
        logging.info('the file:{} already processed'.format(file_log.file_for_analyze))
        return

    path_file_for_analyze = os.path.join(conf["LOG_DIR"], file_log.file_for_analyze)
    raw_data, good_strings, all_time, persent = parse_log(path_file_for_analyze, file_log.ex)
    if persent <= Fraction(conf["LEVEL_PARSE"], 100):
            logging.error('Could not parse more {0}% in {1}. Try to check log format.'.
                          format(conf["LEVEL_PARSE"], path_file_for_analyze))
            return
    logging.debug("parse_log: OK")

    data_to_render = count_stat(raw_data, good_strings, all_time, report_size=conf["REPORT_SIZE"])
    logging.debug("count_stat: OK")

    render_report(data_to_render, report_path)
    logging.info("render_report: OK. Report file: {}".format(report_path))


if __name__ == "__main__":
    parser = create_parser()
    namespace = parser.parse_args()
    try:
        config = parse_config(config, namespace.config)
    except Exception:
        raise Exception("Bad config!")
    try:
        main(config)
    except Exception:
        logging.exception('Unexpected error!')
