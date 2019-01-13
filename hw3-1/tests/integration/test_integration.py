#!/usr/bin/env python
# -*- coding: utf-8 -*-

import functools
import unittest
import json
import hashlib
import redis
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

    def test_z_delete_keys(self):
        for i in self.keys_for_del:
            self.store.storage.delete(i)

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
        self.store_no_connect = api.Storage(host=api.config['STORE_URL'], port=10000,  # bad port, not support by redis
                                            db=api.config['NUMBER_DB'], num_reconnect=api.config['NUM_RECONNECT'])

    def get_response(self, request):
        return api.method_handler({"body": request, "headers": self.headers}, self.context, self.store)

    def set_valid_auth(self, request):
        if request.get("login") == api.ADMIN_LOGIN:
            request["token"] = hashlib.sha512(datetime.now().strftime("%Y%m%d%H") + api.ADMIN_SALT).hexdigest()
        else:
            msg = request.get("account", "") + request.get("login", "") + api.SALT
            request["token"] = hashlib.sha512(msg).hexdigest()

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

    @cases([(['Mikhaylov', 'Vasily'], ['cars', 0])])  
    def test_no_connection_store(self, keys_online, ints):
        res_onl = self.check_store(self.store_no_connect, 'cache_get', keys_online, ints)
        self.assertEqual(res_onl, None)
        res_int = self.check_store(self.store_no_connect, 'get', keys_online, ints)
        self.assertIsInstance(res_int, redis.exceptions.ConnectionError)

    @cases([
        {"first_name": "Mikhaylov", "last_name": "Vasily"},
    ])
    def test_ok_score_request_store(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code, arguments)
        score = response.get("score")
        self.assertTrue(isinstance(score, (int, float)) and score >= 0, arguments)
        self.assertEqual(sorted(self.context["has"]), sorted(arguments.keys()))
        self.assertEqual(score, 10)

    @cases([
        {"client_ids": [0]},
    ])
    def test_ok_interests_request_store(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "clients_interests", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code, arguments)
        self.assertEqual(len(arguments["client_ids"]), len(response))
        self.assertTrue(all(v and isinstance(v, list) and all(isinstance(i, basestring) for i in v)
                            for v in response.values()))
        self.assertEqual(self.context.get("nclients"), len(arguments["client_ids"]))
        self.assertEqual(response[0], ['hi-tech', 'cars'])

    def test_empty_request(self):
        _, code = self.get_response({})
        self.assertEqual(api.INVALID_REQUEST, code)

    @cases([
        {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "", "arguments": {}},
        {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "token": "sdd", "arguments": {}},
        {"account": "horns&hoofs", "login": "admin", "method": "online_score", "token": "", "arguments": {}},
    ])
    def test_bad_auth(self, request):
        _, code = self.get_response(request)
        self.assertEqual(api.FORBIDDEN, code)

    @cases([
        {"account": "horns&hoofs", "login": "h&f", "method": "online_score"},
        {"account": "horns&hoofs", "login": "h&f", "arguments": {}},
        {"account": "horns&hoofs", "method": "online_score", "arguments": {}},
    ])
    def test_invalid_method_request(self, request):
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code)
        self.assertTrue(len(response))

    @cases([
        {},
        {"phone": "79175002040"},
        {"phone": "89175002040", "email": "stupnikov@otus.ru"},
        {"phone": "79175002040", "email": "stupnikovotus.ru"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": -1},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": "1"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.1890"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "XXX"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.2000", "first_name": 1},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.2000",
         "first_name": "s", "last_name": 2},
        {"phone": "79175002040", "birthday": "01.01.2000", "first_name": "s"},
        {"email": "stupnikov@otus.ru", "gender": 1, "last_name": 2},
    ])
    def test_invalid_score_request(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code, arguments)
        self.assertTrue(len(response))

    @cases([
        {"phone": "79175002040", "email": "stupnikov@otus.ru"},
        {"phone": 79175002040, "email": "stupnikov@otus.ru"},
        {"gender": 1, "birthday": "01.01.2000", "first_name": "a", "last_name": "b"},
        {"gender": 0, "birthday": "01.01.2000"},
        {"gender": 2, "birthday": "01.01.2000"},
        {"first_name": "a", "last_name": "b"},
        {"phone": "79175002040", "email": "stupnikov@otus.ru", "gender": 1, "birthday": "01.01.2000",
         "first_name": "a", "last_name": "b"},
    ])
    def test_ok_score_request(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code, arguments)
        score = response.get("score")
        self.assertTrue(isinstance(score, (int, float)) and score >= 0, arguments)
        self.assertEqual(sorted(self.context["has"]), sorted(arguments.keys()))

    def test_ok_score_admin_request(self):
        arguments = {"phone": "79175002040", "email": "stupnikov@otus.ru"}
        request = {"account": "horns&hoofs", "login": "admin", "method": "online_score", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code)
        score = response.get("score")
        self.assertEqual(score, 42)

    @cases([
        {},
        {"date": "20.07.2017"},
        {"client_ids": [], "date": "20.07.2017"},
        {"client_ids": {1: 2}, "date": "20.07.2017"},
        {"client_ids": ["1", "2"], "date": "20.07.2017"},
        {"client_ids": [1, 2], "date": "XXX"},
    ])
    def test_invalid_interests_request(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "clients_interests", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.INVALID_REQUEST, code, arguments)
        self.assertTrue(len(response))

    @cases([
        {"client_ids": [1, 2, 3], "date": datetime.today().strftime("%d.%m.%Y")},
        {"client_ids": [1, 2], "date": "19.07.2017"},
        {"client_ids": [0]},
    ])
    def test_ok_interests_request(self, arguments):
        request = {"account": "horns&hoofs", "login": "h&f", "method": "clients_interests", "arguments": arguments}
        self.set_valid_auth(request)
        response, code = self.get_response(request)
        self.assertEqual(api.OK, code, arguments)
        self.assertEqual(len(arguments["client_ids"]), len(response))
        self.assertTrue(all(v and isinstance(v, list) and all(isinstance(i, basestring) for i in v)
                        for v in response.values()))
        self.assertEqual(self.context.get("nclients"), len(arguments["client_ids"]))


if __name__ == "__main__":
    unittest.main()
