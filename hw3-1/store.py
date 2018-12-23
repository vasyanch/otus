#!/usr/bin/env python
# -*- coding: utf-8 -*-

import redis
import json
import random
import logging
import time


def reconnect(fun):
    def wrapper(*args, **kwargs):
        try:
            logging.debug('Function: {}'.format(fun.__name__))
            return fun(*args, **kwargs)
        except redis.exceptions.ConnectionError:
            if args[0].check_connect():
                return fun(*args, **kwargs)
            else:
                logging.error('Connection to redis is failed! Address: host {0}, port {1}, db {2}'.format(
                    args[0].host, args[0].port, args[0].db))
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
    def __init__(self, host='localhost', port=6379, db=0, num_reconnect=10):
        self.host = host
        self.port = port
        self.db = db
        self.reconnect = num_reconnect
        self.interests = ["cars", "pets", "travel", "hi-tech", "sport",
                          "music", "books", "tv", "cinema", "geek", "otus"]
        self.storage = redis.Redis(host=self.host, port=self.port, db=self.db)

    def check_connect(self):
        i = 0
        while i < self.reconnect:
            try:
                return self.storage.ping()
            except redis.exceptions.ConnectionError:
                time.sleep(0.3)
                i += 1
        else:
            logging.info('{} attempts to connect to the DB is failed!'.format(self.reconnect))
            return False

    @reconnect
    def get(self, key):
        interests_id = self.storage.get(key)
        if not interests_id:
            interests_id = json.dumps(random.sample(self.interests, 2))
            self.storage.set(key, interests_id)
        return interests_id

    @cache
    @reconnect
    def cache_get(self, key):
        val = self.storage.get(key)
        return float(val) if val is not None else None 

    @cache
    @reconnect
    def cache_set(self, key, score, time_store):
        self.storage.set(key, score, time_store)
