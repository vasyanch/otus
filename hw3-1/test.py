#!/usr/bin/env python
# -*- coding: utf-8 -*-

import functools
import unittest
import json
import hashlib
import redis
import api

from datetime import datetime


def cases(cases):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args):
            for c in cases:
                new_args = args + (c if isinstance(c, tuple) else (c,))
                f(*new_args)
        return wrapper
    return decorator


class TestSuite(unittest.TestCase):
    keys_for_del = []
    key_parts = ['first_name', 'last_name', 'phone', 'birthday', 'gender', 'email']

    def test_z_delete_keys(self):
        for i in self.keys_for_del:
            self.store.storage.delete(i)

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

    def check_field(self, cls_field, value):
        try:
            return cls_field.check(value)
        except api.ValidationError:
            return api.ValidationError()

    def keys_for_test(self):
        interests = ["cars", "pets", "travel", "hi-tech"]
        key_parts = [['Mikhaylov', 'Vasily'], ['vasyanch852@gmail.com', '79151950017 '], ['20180101', '1']]
        for k in range(3):
            key_online = "uid:" + hashlib.md5("".join(key_parts[k])).hexdigest()
            self.keys_for_del.append('i:{}'.format(str(k)))
            self.keys_for_del.append(key_online)
            self.store.storage.set('i:{}'.format(str(k)), json.dumps([interests[3], interests[k]]))
            self.store.storage.set(key_online, 10)

    def check_store(self, con_store, method, keys_online, ints):
        ans = None
        if method == 'cache_get':
            ans = con_store.cache_get("uid:" + hashlib.md5("".join(keys_online)).hexdigest())
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

    @cases([1, [1], {1: 1}, 'a'*256, '', 0, [], {}])
    def test_bad_char_field(self, value):
        value = self.check_field(api.CharField(), value)
        self.assertIsInstance(value, api.ValidationError)

    @cases([None, ''])
    def test_nullvalue_char(self, value):
        res = self.check_field(api.CharField(required=True), value)
        self.assertIsInstance(res, api.ValidationError)
        res = self.check_field(api.CharField(nullable=True), value)
        self.assertEqual(res, value)

    @cases(['otus', 'a'*255])
    def test_char_field_ok(self, value):
        res = self.check_field(api.CharField(), value)
        self.assertEqual(res, value)

    @cases([1, [1], 'a', '', [], {}])
    def test_arg_field_bad(self, value):
        res = self.check_field(api.ArgumentsField(), value)
        self.assertIsInstance(res, api.ValidationError)

    @cases([None, {}])
    def test_nullvalue_args(self, value):
        res = self.check_field(api.ArgumentsField(required=True), value)
        self.assertIsInstance(res, api.ValidationError)
        res = self.check_field(api.ArgumentsField(nullable=True), value)
        self.assertEqual(res, value)

    @cases([{'account': 'vasya', 'gender': 1}])
    def test_arg_field_ok(self, value):
        res = self.check_field(api.ArgumentsField(), value)
        self.assertEqual(res, value)

    @cases([1, [1], 'a', '', [], {}])
    def test__email_field_bad(self, value):
        res = self.check_field(api.EmailField(), value)
        self.assertIsInstance(res, api.ValidationError)

    @cases([None, ''])
    def test_nullvalue_email(self, value):
        res = self.check_field(api.EmailField(required=True), value)
        self.assertIsInstance(res, api.ValidationError)
        res = self.check_field(api.EmailField(nullable=True), value)
        self.assertEqual(res, value)

    @cases(['opex23@inbox.ru', 'v@mail.ru'])
    def test_email_field_ok(self, value):
        res = self.check_field(api.EmailField(), value)
        self.assertEqual(res, value)

    @cases([1, [1], 'a', '', [], {}, 'a'*11, '7'+'8'*11, '8'*11,
            89151950018, 123, 789, 791519511177])
    def test_phone_field_bad(self, value):
        res = self.check_field(api.PhoneField(), value)
        self.assertIsInstance(res, api.ValidationError)

    @cases([None, ''])
    def test_nullvalue_phone(self, value):
        res = self.check_field(api.PhoneField(required=True), value)
        self.assertIsInstance(res, api.ValidationError)
        res = self.check_field(api.PhoneField(nullable=True), value)
        self.assertEqual(res, value)

    @cases([79151950018, '79151950018'])
    def test_phone_field_ok(self, value):
        res = self.check_field(api.PhoneField(), value)
        self.assertEqual(res, str(value))

    @cases([1, [1], 'a', '', [], {}, '2014.01.01', '33.01.2014', '01.01.001',
            '01.32.2014', '12.20.2014'])
    def test_date_field_bad(self, value):
        res = self.check_field(api.DateField(), value)
        self.assertIsInstance(res, api.ValidationError)

    @cases([None, ''])
    def test_nullable_date(self, value):
        res = self.check_field(api.DateField(required=True), value)
        self.assertIsInstance(res, api.ValidationError)
        res = self.check_field(api.DateField(nullable=True), value)
        self.assertEqual(res, value)

    @cases(['01.01.2014', '30.12.2018'])
    def test_date_field_ok(self, value):
        res = self.check_field(api.DateField(), value)
        self.assertEqual(res, datetime.strptime(value, '%d.%m.%Y'))

    @cases(['01.11.1948', '01.01.1900', '01.01.2020'])
    def test_birth_field_bad(self, value):
        res = self.check_field(api.BirthDayField(), value)
        self.assertIsInstance(res, api.ValidationError)

    @cases(['01.10.1991', '13.12.2018'])
    def test_birth_field_ok(self, value):
        res = self.check_field(api.BirthDayField(), value)
        self.assertEqual(res, datetime.strptime(value, '%d.%m.%Y'))

    @cases([[1], 'a', '', [], {}, 5, -1])
    def test_gender_field_bad(self, value):
        res = self.check_field(api.GenderField(), value)
        self.assertIsInstance(res, api.ValidationError)

    @cases([0, 1, 2])
    def test_gender_field_ok(self, value):
        res = self.check_field(api.GenderField(), value)
        self.assertEqual(res, value)        

    @cases(
        [1, {1: 1}, 'a', {1, 2}, 0, '', [], {}, ['a'], [[1]], [{1: 1}], [(1,)], [[]], [()]])
    def test_clientids_field_bad(self, value):
        res = self.check_field(api.ClientIDsField(), value)
        self.assertIsInstance(res, api.ValidationError)

    @cases([None, []])
    def test_nullable_clinerids(self, value):
        res = self.check_field(api.ClientIDsField(required=True), value)
        self.assertIsInstance(res, api.ValidationError)
        res = self.check_field(api.ClientIDsField(nullable=True), value)
        self.assertEqual(res, value)

    @cases([[1], [1, 2]])
    def test_clientids_field_ok(self, value):
        res = self.check_field(api.ClientIDsField(), value)
        self.assertEqual(res, value)
    
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
