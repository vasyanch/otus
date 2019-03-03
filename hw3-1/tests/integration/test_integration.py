#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import json
import hashlib
import redis
import os

from api import api
from tests.cases import cases


class MyMock:
    def __init__(self, side_effect=None):
        self.side_effect = side_effect
        self.call_count = 0

    def __call__(self, *args, **kwargs):
        self.call_count += 1
        raise self.side_effect


def parse_redis_host():
    redis_host = os.getenv('REDIS_HOST_API')
    if redis_host:
        store_url, store_port, number_db = redis_host.split(":")
        return dict(STORE_URL=store_url, STORE_PORT=store_port, NUMBER_DB=number_db)


STORE_HOST = parse_redis_host()


@unittest.skipIf(not STORE_HOST, "REDIS_HOST_API is not in os.environ. "
                                 "You should define REDIS_HOST_API  environment variable for integration tests.")
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
            self.store.set('i:{}'.format(str(k)), json.dumps([interests[3], interests[k]]))
            self.store.set(key_online, 10)

    def setUp(self):
        self.store = api.Storage(host=STORE_HOST['STORE_URL'], port=STORE_HOST['STORE_PORT'],
                                 db=STORE_HOST['NUMBER_DB'])

        self.fake_store = api.Storage(host='___')
        self.keys_for_test()

    def tearDown(self):
        for i in self.keys_for_del:
            self.store.storage.delete(i)

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
        res_onl = self.fake_store.cache_get("uid:" + hashlib.md5("".join(keys_online)).hexdigest())
        self.assertEqual(res_onl, None)
        self.assertRaises(redis.exceptions.ConnectionError, self.fake_store.get, 'i:{}'.format(str(ints[1])))

    def test_reconnect(self):
        self.fake_store.storage.get = MyMock(side_effect=redis.exceptions.ConnectionError())
        self.assertRaises(redis.exceptions.ConnectionError, self.fake_store.get, 'i')
        self.assertEqual(self.fake_store.storage.get.call_count, self.fake_store.num_reconnect)


if __name__ == "__main__":
    unittest.main()
