# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 31 14:07:25 2018

@author: Mickhailov
"""

import unittest
import logging
import os
import shutil
from collections import namedtuple
from log_analyzer import parse_config, find_log, parse_log, count_stat, main
from datetime import datetime
from fractions import Fraction


class MyListTest(unittest.TestCase):

    def test_config_empty_file(self):
        config = dict(REPORT_SIZE=1000, REPORT_DIR="./test/reports", LOG_DIR="./test/log", LEVEL_PARSE=50,
                      LOGGING_LEVEL=logging.DEBUG, LOGGING_TO_FILE=None)
        res = parse_config(config, './test/test_configs/empty_file')
        self.assertEqual(res, config)

    def test_config_few_options(self):
        config = dict(REPORT_SIZE=1000, REPORT_DIR="./test/reports", LOG_DIR="./test/log", LEVEL_PARSE=50,
                      LOGGING_LEVEL=logging.DEBUG, LOGGING_TO_FILE=None)
        res = parse_config(config, './test/test_configs/few_options')
        test_config = dict(REPORT_SIZE=500, REPORT_DIR='./test/test_dir', LOG_DIR='./test/log',
                           LOGGING_TO_FILE='./test/test_dir/test.log', LOGGING_LEVEL=logging.ERROR, LEVEL_PARSE=50)
        self.assertEquals(res, test_config)

    def test_config_another_config(self):
        config = dict(REPORT_SIZE=1000, REPORT_DIR="./test/reports", LOG_DIR="./test/log", LEVEL_PARSE=50,
                      LOGGING_LEVEL=logging.DEBUG, LOGGING_TO_FILE=None)
        res = parse_config(config, './test/test_configs/another_config')
        test_config = dict(REPORT_SIZE=500, REPORT_DIR='./test/test_dir',
                           LOG_DIR='./test/test_dir',
                           LOGGING_TO_FILE='./test/test_dir/test.log',
                           LOGGING_LEVEL=logging.ERROR, LEVEL_PARSE=20)
        self.assertEquals(res, test_config)

    def test_find_log_real_file(self):
        res = find_log('./test/test_logs_nginx')
        Log = namedtuple('Log', 'file_for_analyze date ex')
        self.assertEqual(res, Log('nginx-access-ui.log-20200413.gz',
                                  datetime.strptime('20200413', '%Y%m%d'), 'gz'))

    def test_find_log_bz2(self):
        res = find_log('./test/test_logs_nginx/test_bz2')
        Log = namedtuple('Log', 'file_for_analyze date ex')
        self.assertEquals(res, Log('nginx-access-ui.log-20150413',
                                   datetime.strptime('20150413', '%Y%m%d'), None))

    def test_find_log_gz(self):
        res = find_log('./test/test_logs_nginx/test_gz')
        Log = namedtuple('Log', 'file_for_analyze date ex')
        self.assertEquals(res, Log('nginx-access-ui.log-20220413.gz',
                                   datetime.strptime('20220413', '%Y%m%d'), 'gz'))

    def test_find_log_no_file(self):
        res = find_log('./test/test_logs_nginx/test_no_file')
        self.assertEquals(res, None)

    def test_parse_log_empty_file(self):
        res = parse_log('./test/test_configs/empty_file', None)
        self.assertEquals(res, ({}, 0, 0, 0))

    def test_parse_log_gz_file(self):
        res = parse_log('./test/test_logs_nginx/nginx-access-ui.log-20200413.gz', 'gz')
        parse = ({'/api/v2/banner/25019354': [0.390],
                  '/api/1/photogenic_banners/list/?server_name=WIN7RB4': [0.133],
                  '/api/v2/banner/16852664': [0.199]}, 3, 0.722, Fraction(3, 35))
        self.assertEquals(res, parse)

    def test_count_stat(self):
        arguments = namedtuple('arguments', 'data num_req all_time')
        data = {}
        num_req = 1
        all_time = 0
        for i in ('a', 'b'):
            num_req += 1
            data[i] = [j * 2 * 1.0 for j in range(num_req)]
            all_time += sum(data[i])
        num_req = sum([len(p) for p in data.values()])
        res = count_stat(*arguments(data, num_req, all_time))
        self.assertEquals(res, [dict(url='b', time_sum=6.0, count=3, count_perc=60.0,
                                     time_perc=75.0, time_avg=2.0, time_med=2.0,
                                     time_max=4.0),
                                dict(url='a', time_sum=2.0, count=2, count_perc=40.0,
                                     time_perc=25.0, time_avg=1.0, time_med=0.0,
                                     time_max=2.0)])

    def test_main1(self):
        config = dict(REPORT_SIZE=1000, REPORT_DIR="./test/reports", LOG_DIR="./test/test_logs_nginx/", LEVEL_PARSE=50,
                      LOGGING_LEVEL=logging.INFO, LOGGING_TO_FILE= './test/log_analyzer.log')
        main(config)

        res1 = os.path.exists('./test/log_analyzer.log')
        with open('./test/log_analyzer.log', 'r') as f:
            res2 = f.readlines()[-1][28:]
        shutil.rmtree('./test/reports')
        os.remove('./test/log_analyzer.log')
        self.assertEquals(res1, True)
        self.assertEquals(res2, 'Could not parse more 50% in ./test/test_logs_nginx/nginx-access-ui.log-20200413.gz. \
Try to check log format.\n')

    def test_main(self):
        config = dict(REPORT_SIZE=1000, REPORT_DIR="./test/reports", LOG_DIR="./test", LEVEL_PARSE=50,
                      LOGGING_LEVEL=logging.INFO, LOGGING_TO_FILE='./test/log_analyzer.log')
        main(config)
        res1 = os.path.exists('./test/log_analyzer.log')
        with open('./test/log_analyzer.log', 'r') as f:
            res2 = f.readlines()[-1][28:]
        res3 = os.path.exists('./test/reports/report-2017.06.30.html')
        main(config)
        with open('./test/log_analyzer.log', 'r') as f:
            res4 = f.readlines()[-1][28:]
        shutil.rmtree('./test/reports')
        self.assertEquals(res1, True)
        path_report = os.path.join(os.path.abspath(os.path.dirname(__file__)), config['REPORT_DIR'])
        self.assertEquals(res2, 'render_report: OK. Report file: ./test/reports/report-2017.06.30.html\n')
        self.assertEquals(res3, True)
        self.assertEquals(res4, 'the file:nginx-access-ui.log-20170630 already processed\n')


if __name__ == '__main__':
    unittest.main()
