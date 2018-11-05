# !/usr/bin/env python
# -*- coding: utf-8 -*-


# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';
# sys.argv -> ['file_name.py', 'dir_log_nginx', 'config']

import sys
import re
import gzip
import json
import argparse
import configparser
import logging
import os
from collections import namedtuple
from string import Template
from fractions import Fraction


config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log",
    "LEVEL_PARSE": 10,
    "LOGGING_LEVEL": logging.DEBUG,
    "LOGGING_TO_FILE": None
}


def create_parser():
    default = u"{}/config_log_analyzer".format(os.path.dirname(os.path.abspath(__file__)))
    parser_ = argparse.ArgumentParser()
    parser_.add_argument('-c', '--config', default=default)
    return parser_


def parse_config(default_config, path):
    
    def check_option(outer_config, key, value):
        check = 0
        if key in ('report_size', 'level_parse') and re.match(r'\d+$', value) and \
           ((key == 'report_size' and int(value) > 0) or (key == 'level_parse' and 0 < int(value) <= 100)):
            outer_config[key] = int(value)
            check = 1
        elif key in ('report_dir', 'log_dir', 'logging_to_file') and os.path.exists(value):
            check = 1
        elif key == 'logging_level' and value in ('INFO', 'DEBUG', 'ERROR'):
            check = 1
            if value == 'INFO':
                outer_config[key] = logging.INFO
            elif value == 'DEBUG':
                outer_config[key] = logging.DEBUG
            else:
                outer_config[key] = logging.ERROR
        else:
            pass
        return outer_config if check else False
    
    if os.path.exists(path):
        try:
            priority_config = configparser.ConfigParser()
            priority_config.read(path)
            if not priority_config.sections():
                return default_config
            priority_config = dict(priority_config.items('Config_log_analyzer'))
            for item in priority_config.items():
                priority_config = check_option(priority_config, *item)
                if priority_config:
                    default_config[item[0].upper()] = priority_config[item[0]]
                else:
                    return 'bad option:{} in config file!'.format(item[0].upper())
            return default_config
        except Exception:
            return 'bad config!'
    else:
        return 'Bad path to config:{}'.format(path) 


def find_log(dir_log_nginx):
    log = namedtuple('log', 'file_for_analyze date ex')
    maximum = 0
    file_for_analyze = ''
    date = 0
    ex = None
    for file_ in os.listdir(dir_log_nginx):
        if re.match(r'nginx-access-ui.log-\d{8}((\.gz)|$)', file_):
            date_and_ex = file_.split('-')[-1]
            date_and_ex = date_and_ex.split('.')
            cur_date = int(date_and_ex[0])
            maximum = max(maximum, cur_date)
            if cur_date == maximum:
                file_for_analyze = file_
                try:
                    date, ex = cur_date, date_and_ex[1]
                except IndexError:
                    date, ex = cur_date, None
    return log(file_for_analyze, date, ex)


def parse_string(file_from):
    req = namedtuple('req', 'url time')
    for line in file_from.readlines():
        lst = line.split()
        pattern_ip = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
        pattern_url = r'(/\w*)+'
        pattern_time = r'\d+(\.\d+)'
        try:
            if re.match(pattern_ip, lst[0]) and re.match(pattern_url, lst[6]) and re.match(pattern_time, lst[-1]):
                url, time = lst[6], float(lst[-1])
                yield req(url, time)
            else:
                yield 'bad string'
        except IndexError:
            yield 'bad string'


def parse_log(path_file_for_analyze, ex):
    if ex is None:
        file_log = open(path_file_for_analyze, 'r')
    else:
        file_log = gzip.open(path_file_for_analyze, 'rb')
    data = dict()
    all_time = 0
    all_strings = 0
    good_strings = 0
    for string_log in parse_string(file_log):
        all_strings += 1
        if string_log != 'bad string':
            good_strings += 1
            all_time += string_log.time
            key = string_log.url
            if key not in data:
                data[key] = [string_log.time]
            else:
                data[key].append(string_log.time)
    file_log.close()
    return data, good_strings, all_strings, all_time


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


def render_report(data_to_render_, date, report_dir):
    table_json = json.dumps(data_to_render_, indent=4)
    report = open('report.html', 'r')
    report_to_file = Template(report.read())
    report.close()
    report_to_file = report_to_file.safe_substitute(table_json=table_json)
    path_report = '{0}/report-{1}.{2}.{3}.html'.format(report_dir, date[0:4], date[4:6], date[6:8])
    report_date = open(path_report, 'w')
    report_date.write(report_to_file)
    report_date.close()
    return path_report


def main(config):
    file_log = find_log(config["LOG_DIR"])
    if file_log.file_for_analyze != '':
        last_file_log = open('last_file_log', 'r')
        if file_log.file_for_analyze == last_file_log.read():
            logging.error('the file:{} alredy processed'.format(file_log.file_for_analyze))
            last_file_log.close()
            sys.exit(1)
        last_file_log.close()
    else:
        logging.error('file_for_analyze is not found.')
        sys.exit(1)
    logging.debug("find_log: {} OK".format(file_log.file_for_analyze))
        
    path_file_for_analyze = '{0}/{1}'.format(config["LOG_DIR"], file_log.file_for_analyze)
    raw_data, good_strings, all_strings, all_time = parse_log(path_file_for_analyze, file_log.ex)
    if all_strings > 0:
        if Fraction(good_strings, all_strings) <= Fraction(config["LEVEL_PARSE"], 100):
            logging.error('Could not parse more {0}% in {1}. \
                            Try to check log format.'.format(config["LEVEL_PARSE"],
                                                              path_file_for_analyze))
            sys.exit(1)
    else:
        logging.error('{} file is empty!'.format(path_file_for_analyze))
        sys.exit(1)
    logging.debug("parse_log: OK")
    data_to_render = count_stat(raw_data, good_strings, all_time,
                                    report_size=config["REPORT_SIZE"])
    logging.debug("count_stat: OK")
    path_report = render_report(data_to_render, str(file_log.date), report_dir=config["REPORT_DIR"])
    logging.info("render_report: OK. Report file: {}".format(path_report))
    last_file_log = open('last_file_log', 'w')
    last_file_log.write(file_log.file_for_analyze)
    last_file_log.close()
    logging.debug("last_file_log is update: OK")


if __name__ == "__main__":
    parser = create_parser()
    namespace = parser.parse_args()
    config = parse_config(config, namespace.config)  # type(namespace.config) -> str
    if type(config) is not dict:
        raise Exception, config

    logging.basicConfig(format='[%(asctime)s] %(levelname).1s %(message)s', level=config["LOGGING_LEVEL"],
                        filename=config["LOGGING_TO_FILE"])
    try:
        main(config)
    except Exception:
        logging.exception('Unexpected error!')
