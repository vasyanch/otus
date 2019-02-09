#!/usr/bin/env python
# -*- coding: utf-8 -*-

import redis
import logging
import time
import functools


def reconnect(num_attempts):
    def deco(fun):
        @functools.wraps(fun)
        def wrapper(self, *args, **kwargs):
            for i in range(num_attempts):
                try:
                    logging.debug('Function: {}'.format(fun.__name__))
                    return fun(self, *args, **kwargs)
                except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError) as e:
                    time.sleep(0.3)
            raise e
        return wrapper
    return deco


def cache(fun):
    def wrapper(*args, **kwargs):
        try:
            return fun(*args, **kwargs)
        except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError):
            return
    return wrapper


class Storage(object):
    num_reconnect = 5

    def __init__(self, host='localhost', port=6379, db=0, timeout=2):
        self.host = host
        self.port = port
        self.db = db
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

    @reconnect(num_reconnect)
    def get(self, key):
        return self.storage.get(key)

    @cache
    @reconnect(num_reconnect)
    def cache_get(self, key):
        val = self.storage.get(key)
        return val if val is not None else None

    @cache
    @reconnect(num_reconnect)
    def cache_set(self, key, score, time_store):
        self.storage.set(key, score, time_store)
