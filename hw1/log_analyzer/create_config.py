# !/usr/bin/env python
# -*- coding: utf-8 -*-

import configparser


def create_config(path):
    config = configparser.ConfigParser()
    config.add_section('Config_log_analyzer')
    config.set('Config_log_analyzer', 'REPORT_SIZE', '1000')
    config.set('Config_log_analyzer', 'REPORT_DIR', './reports')
    config.set('Config_log_analyzer', 'LOG_DIR', './log')
    config.set('Config_log_analyzer', 'LOGGING_TO_FILE', './log_analyzer.log')
    config.set('Config_log_analyzer', 'LOGGING_LEVEL', 'DEBUG')
    config.set('Config_log_analyzer', 'LEVEL_PARSE', '50')

    with open(path, 'w') as config_file:
        config.write(config_file)


if __name__ == '__main__':
    path = './config_log_analyzer'
    create_config(path)
    import os
    print  os.path.join(os.path.dirname(os.path.abspath(__file__)), 'REPORT_DIR')
    print os.path.join(os.path.dirname(os.path.abspath(__file__)), '/home')