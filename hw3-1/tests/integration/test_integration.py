#!/usr/bin/env python
# -*- coding: utf-8 -*-

import functools
import unittest
import json
import hashlib
import redis
import time

from api import api
from datetime import datetime


def cases(cases):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args):
            for c in cases:
                new_args = args + (c if isinstance(c, tuple) else (c,))
                try:
                    f(*new_args)
                except Exception as e:
                    print '\nTest --> {0}\nthis case: ({1}) is broken!'.format(f.__name__, c)
                    raise e
        return wrapper
    return decorator


class TestSuite(unittest.TestCase):
    keys_for_del = []
    key_parts = ['first_name', 'last_name', 'phone', 'birthday', 'gender', 'email']

    def keys_for_test(self):
        interests = ["cars", "pets", "travel", "hi-tech"]
        key_parts = [['Mikhaylov', 'Vasily'], ['vasyanch852@gmail.com', '79151950017 '], ['20180101', '1']]
        for k in range(3):
            key_online = "uid:" + hashlib.md5("".join(key_parts[k])).hexdigest()
            self.keys_for_del.append('i:{}'.format(str(k)))
            self.keys_for_del.append(key_online)
            self.store.storage.set('i:{}'.format(str(k)), json.dumps([interests[3], interests[k]]))
            self.store.storage.set(key_online, 10)

    def setUp(self):
        self.context = {}
        self.headers = {}
        self.store = api.Storage(host=api.config['STORE_URL'], port=api.config['STORE_PORT'],
                                 db=api.config['NUMBER_DB'], num_reconnect=api.config['NUM_RECONNECT'])
        self.keys_for_test()

    def tearDown(self):
        for i in self.keys_for_del:
            self.store.storage.delete(i)

    def check_store(self, con_store, method, keys_online, ints):
        ans = None
        if method == 'cache_get':
            ans = con_store.cache_get("uid:" + hashlib.md5("".join(keys_online)).hexdigest())
            ans = int(ans) if ans else None
        if method == 'get':
            try:
                ans = con_store.get('i:{}'.format(str(ints[1])))
            except redis.exceptions.ConnectionError:
                ans = redis.exceptions.ConnectionError()
        return ans

    def test_connection_store(self):
        res = self.store.check_connect()
        self.assertEqual(res, True, "can't connect to database(redis)")
    
    @cases([
        (['Mikhaylov', 'Vasily'], ['cars', 0]),
        (['vasyanch852@gmail.com', '79151950017 '], ['pets', 1]),
        (['20180101', '1'], ['travel', 2])
        ])
    def test_store(self, keys_online, ints):
        res_onl = self.check_store(self.store, 'cache_get', keys_online, ints)
        self.assertEqual(res_onl, 10)
        res_int = self.check_store(self.store, 'get', keys_online, ints)
        self.assertEqual(res_int, json.dumps(['hi-tech', ints[0]]))


if __name__ == "__main__":
    unittest.main()
