# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 31 14:07:25 2018

@author: Mickhailov
"""

import unittest
import logging
from collections import namedtuple
from log_analyzer import parse_config, find_log, parse_log, count_stat, config


class MyListTest(unittest.TestCase):
    
    def test_config_bad_path(self):
        res = parse_config(config, '')
        self.assertEqual(res, 'Bad path to config:')
        
    def test_config_empty_file(self):
        res = parse_config(config, './test_configs/empty_file')
        self.assertEqual(res, config)
        
    def test_config_wrong_sintax(self):
        res = parse_config(config, './test_configs/wrong_sintax')
        self.assertEqual(res, 'bad config!')
    
    def test_config_bad_report_size(self):
        res = parse_config(config, './test_configs/bad_report_size')
        self.assertEqual(res, 'bad option:REPORT_SIZE in config file!')
    
    def test_config_bad_report_dir(self):
        res = parse_config(config, './test_configs/bad_report_dir')
        self.assertEquals(res, 'bad option:REPORT_DIR in config file!')
    
    def test_config_bad_log_dir(self):
        res = parse_config(config, './test_configs/bad_log_dir')
        self.assertEquals(res, 'bad option:LOG_DIR in config file!')
        
    def test_config_bad_logging_to_file(self):
        res = parse_config(config, './test_configs/bad_logging_to_file')
        self.assertEquals(res, 'bad option:LOGGING_TO_FILE in config file!')
    
    def test_config_bad_logging_level(self):
        res = parse_config(config, './test_configs/bad_logging_level')
        self.assertEquals(res, 'bad option:LOGGING_LEVEL in config file!')
        
    def test_config_bad_level_parse(self):
        res = parse_config(config, './test_configs/bad_level_parse')
        self.assertEquals(res, 'bad option:LEVEL_PARSE in config file!')
        
    def test_config_another_config(self):
        res = parse_config(config, './test_configs/another_config')
        test_config = dict(REPORT_SIZE=500, REPORT_DIR='./test_dir',
                           LOG_DIR='./test_dir',
                           LOGGING_TO_FILE='./test_dir/test.log',
                           LOGGING_LEVEL=logging.ERROR, LEVEL_PARSE=20)
        self.assertEquals(res, test_config)
        
    def test_config_few_options(self):
        res = parse_config(config, './test_configs/few_options')
        test_config = dict(REPORT_SIZE=500, REPORT_DIR='./test_dir',
                           LOG_DIR='./',
                           LOGGING_TO_FILE='./test_dir/test.log',
                           LOGGING_LEVEL=logging.ERROR, LEVEL_PARSE=50)
        self.assertEquals(res, test_config)

    def test_find_log_real_file(self):
        res = find_log('./test_logs_nginx')
        Log = namedtuple('Log', 'file_for_analyze date ex')
        self.assertEqual(res, Log('nginx-access-ui.log-20200413', 
                                  20200413, None))
        
    def test_find_log_bz2(self):
        res = find_log('./test_logs_nginx/test_bz2')
        Log = namedtuple('Log', 'file_for_analyze date ex')
        self.assertEquals(res, Log('nginx-access-ui.log-20150413', 
                                   20150413, None))
    
    def test_find_log_gz(self):
        res = find_log('./test_logs_nginx/test_gz')
        Log = namedtuple('Log', 'file_for_analyze date ex')
        self.assertEquals(res, Log('nginx-access-ui.log-20220413.gz', 
                                   20220413, 'gz'))

    def test_find_log_no_file(self):
        res = find_log('./test_logs_nginx/test_no_file')
        Log = namedtuple('Log', 'file_for_analyze date ex')
        self.assertEquals(res, Log('', 0, None))
        
    def test_parse_log_empty_file(self):
        res = parse_log('./test_configs/empty_file', None)
        self.assertEquals(res, ({}, 0, 0, 0))
        
    def test_parse_log_gz_file(self):
        res = parse_log('./test_logs_nginx/nginx-access-ui.log-20000413.gz', 'gz')
        parse = ({'/api/v2/banner/25019354': [0.390],
                      '/api/1/photogenic_banners/list/?server_name=WIN7RB4': [0.133],
                      '/api/v2/banner/16852664': [0.199]}, 3, 35, 0.722)
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


if __name__ == '__main__':
    unittest.main()
