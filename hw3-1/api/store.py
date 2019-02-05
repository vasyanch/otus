#!/usr/bin/env python
# -*- coding: utf-8 -*-

import redis
import json
import random
import logging
import time


def try_reconnect(fun):
    def wrapper(self, *args, **kwargs):
        try:
            logging.debug('Function: {}'.format(fun.__name__))
            return fun(self, *args, **kwargs)
        except redis.exceptions.ConnectionError:
            if self.reconnect():
                return fun(self, *args, **kwargs)
            else:
                logging.error('Connection to redis is failed! Address: host {0}, port {1}, db {2}'.format(
                    self.host, self.port, self.db))
                raise redis.exceptions.ConnectionError
    return wrapper


def cache(fun):
    def wrapper(*args, **kwargs):
        try:
            return fun(*args, **kwargs)
        except redis.exceptions.ConnectionError:
            return
    return wrapper


class Storage(object):
    def __init__(self, host='localhost', port=6379, db=0, num_reconnect=10, timeout=2):
        self.host = host
        self.port = port
        self.db = db
        self.num_reconnect = num_reconnect
        self.timeout = timeout
        self.interests = ["cars", "pets", "travel", "hi-tech", "sport",
                          "music", "books", "tv", "cinema", "geek", "otus"]
        self.storage = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            socket_timeout=self.timeout,
            socket_connect_timeout=self.timeout
        )

    def check_connect(self):
        try:
            return self.storage.ping()
        except redis.exceptions.ConnectionError:
            return False

    def reconnect(self):
        i = 0
        while i < self.num_reconnect:
            if self.check_connect():
                return True
            else:
                time.sleep(0.3)
                i += 1
        else:
            logging.info('{} attempts to connect to the DB is failed!'.format(self.num_reconnect))
            return False

    @try_reconnect
    def get(self, key):
        return self.storage.get(key)

    @cache
    @try_reconnect
    def cache_get(self, key):
        val = self.storage.get(key)
        return val if val is not None else None

    @cache
    @try_reconnect
    def cache_set(self, key, score, time_store):
        self.storage.set(key, score, time_store)
