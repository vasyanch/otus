#!/usr/bin/env python3

import argparse
import os
import logging
import multiprocessing

from webServer import HttpHandler, WebServer
from collections import defaultdict

config = defaultdict(
    host='127.0.0.1',
    )


def parse_config(default_config, args):
    default_config['port'] = int(args.port)
    default_config['num_workers'] = int(args.workers)
    default_config['level_log'] = args.level_log
    default_config['document_root'] = args.root_document
    default_config['file_log'] = args.file_log
    return default_config


def run(conf):
    processes = []
    level = logging.DEBUG if conf['level_log'] == 'debug' else logging.INFO

    try:
        for i in range(conf['num_workers']):
            server = WebServer(http_handler=HttpHandler, host=conf['host'], port=conf['port'],
                               document_root=conf['document_root'])
            p = multiprocessing.Process(target=server.serve_forever, name='worker {}'.format(i))
            processes.append(p)
            logging.basicConfig(filename=conf['file_log'], level=level,
                                format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
            p.start()
            logging.info('Server running on the process: worker {0} PID: {1} host: {2}, port: {3}'.format(
                i, p.pid, conf['host'], conf['port']))
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        for p in processes:
            if p:
                pid, name = p.pid, p.name
                logging.debug('Trying to shutting down process: [name: {0} PID: {1}]'.format(name, pid))
                p.terminate()
                logging.info('Process: [name: {0} PID: {1}] terminated...'.format(name, pid))


if __name__ == '__main__':
    args_parse = argparse.ArgumentParser()
    args_parse.add_argument('-p', '--port', default='80')
    args_parse.add_argument('-w', '--workers', default='4')
    args_parse.add_argument('-l', '--level_log', default='info')
    args_parse.add_argument('-r', '--root_document',
                            default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'DOCUMENT_ROOT'))
    args_parse.add_argument('-f', '--file_log',
                            default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'httpd.log'))
                            
    outer_config = args_parse.parse_args()
    try:
        config = parse_config(config, outer_config)
    except Exception:
        raise Exception("Bad configuration!")
    run(config)
