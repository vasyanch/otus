#!/usr/bin/env python
# -*- coding: utf-8 -*-

import redis
import json
import random


class Storage(object):
    def __init__(self, host='localhost', port=6379, db=0, reconnect=10):
        self.host = host
        self.port = port
        self.db = db
        self.reconnect = reconnect
        self.interests = ["cars", "pets", "travel", "hi-tech", "sport",
                          "music", "books", "tv", "cinema", "geek", "otus"]
        self.storage = self.connect()

    def connect(self):
        i = 0
        while True: #i < self.reconnect:
            try:
                connect = redis.StrictRedis(host=self.host, port=self.port, db=self.db)
                print self.db
                connect.client_list()
                return connect
            except redis.exceptions.ConnectionError:
                i += 1
                continue

    def get(self, key):
        interests_id = self.storage.get(key)
        if not interests_id:
            interests_id = json.dumps(random.sample(self.interests, 2))
            self.storage.set(key, interests_id)
        return interests_id

    def cache_get(self, key):
        try:
            val = self.storage.get(key)
            return float(val) if val is not None else None
        except redis.ConnectionError:
            return None

    def cache_set(self, key, score, time):
        try:
            self.storage.set(key, score, time)
        except redis.ConnectionError:
            pass
