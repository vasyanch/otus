# !/usr/bin/env python
# -*- coding: utf-8 -*-

import configparser


def create_config(path):
    config = configparser.ConfigParser()
    config.add_section('Config_api')
    config.set('Config_api', 'LOGGING_TO_FILE', 'api.log')
    config.set('Config_api', 'PORT', '8080')
    config.set('Config_api', 'LOGGING_LEVEL', 'DEBUG')

    with open(path, 'w') as config_file:
        config.write(config_file)


if __name__ == '__main__':
    path = './config_api'
    create_config(path)
    import os
    print  os.path.join(os.path.dirname(os.path.abspath(__file__)), 'REPORT_DIR')
    print os.path.join(os.path.dirname(os.path.abspath(__file__)), '/home')