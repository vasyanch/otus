#!/usr/bin/env python
# -*- coding: utf-8 -*-

import functools
import unittest
import json
import hashlib
import redis
import time
import fakeredis

from datetime import datetime
from api import api


def cases(cases):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args):
            for c in cases:
                new_args = args + (c if isinstance(c, tuple) else (c,))
                try:
                    f(*new_args)
                except Exception as e:
                    print("\nTest --> {0}\nthis case: ({1}) is broken!".format(f.__name__, c))
                    raise e
        return wrapper
    return decorator


class MyMock:
    def __init__(self, side_effect=None):
        self.side_effect = side_effect
        self.call_count = 0

    def __call__(self, *args, **kwargs):
        self.call_count += 1
        raise self.side_effect


class TestSuite(unittest.TestCase):
    key_parts = ['first_name', 'last_name', 'phone', 'birthday', 'gender', 'email']

    def keys_for_test(self):
        interests = ["cars", "pets", "travel", "hi-tech"]
        key_parts = [['Mikhaylov', 'Vasily'], ['vasyanch852@gmail.com', '79151950017 '], ['20180101', '1']]
        for k in range(3):
            key_online = "uid:" + hashlib.md5("".join(key_parts[k])).hexdigest()
            self.store.storage.set('i:{}'.format(str(k)), json.dumps([interests[3], interests[k]]))
            self.store.storage.set(key_online, 10)

    def setUp(self):
        self.store = api.Storage()
        self.store.storage = fakeredis.FakeStrictRedis()
        self.fakestore = api.Storage()
        fakeserver = fakeredis.FakeServer()
        fakeserver.connected = False
        self.fakestore.storage = fakeredis.FakeStrictRedis(server=fakeserver)
        self.keys_for_test()

    @cases([
        (['Mikhaylov', 'Vasily'], ['cars', 0]),
        (['vasyanch852@gmail.com', '79151950017 '], ['pets', 1]),
        (['20180101', '1'], ['travel', 2])
        ])
    def test_store(self, keys_online, ints):
        res_onl = float(self.store.cache_get("uid:" + hashlib.md5("".join(keys_online)).hexdigest()))
        self.assertEqual(res_onl, 10)
        res_int = self.store.get('i:{}'.format(str(ints[1])))
        self.assertEqual(res_int, json.dumps(['hi-tech', ints[0]]))

    @cases([
        (['Mikhaylov', 'Vasily'], ['cars', 0]),
    ])
    def test_no_connection_store(self,  keys_online, ints):
        res_onl = self.fakestore.cache_get("uid:" + hashlib.md5("".join(keys_online)).hexdigest())
        self.assertEqual(res_onl, None)
        try:
            res_int = self.fakestore.get('i:{}'.format(str(ints[1])))
        except redis.exceptions.ConnectionError:
            res_int = redis.exceptions.ConnectionError()
        self.assertIsInstance(res_int, redis.exceptions.ConnectionError)

    def test_reconnect(self):
        self.fakestore.storage.get = MyMock(side_effect=redis.exceptions.ConnectionError())
        try:
            self.fakestore.get('i')
        except redis.exceptions.ConnectionError:
            pass
        self.assertEqual(self.fakestore.storage.get.call_count, self.fakestore.num_reconnect)


if __name__ == "__main__":
    unittest.main()
