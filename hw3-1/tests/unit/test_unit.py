import datetime
import functools
import unittest
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


def check_field(cls_field, value):
    try:
        return cls_field.check(value)
    except api.ValidationError:
        return api.ValidationError()


class TestCharField(unittest.TestCase):

    @cases([1, [1], {1: 1}, 'a'*256, 0, '', [], {}])
    def test_bad_char(self, value):
        res = check_field(api.CharField(), value)
        self.assertIsInstance(res, api.ValidationError)

    @cases([None, ''])
    def test_nullvalue_char(self, value):
        res = check_field(api.CharField(required=True), value)
        self.assertIsInstance(res, api.ValidationError)
        res = check_field(api.CharField(nullable=True), value)
        self.assertEqual(res, value)

    @cases(['otus', 'a'*255])
    def test_ok_char(self, value):
        res = check_field(api.CharField(), value)
        self.assertEqual(res, value)


class TestArgumentField(unittest.TestCase):

    @cases([1, [1], 'a', '', [], {}])
    def test_bad_args(self, value):
        res = check_field(api.ArgumentsField(), value)
        self.assertIsInstance(res, api.ValidationError)

    @cases([None, {}])
    def test_nullvalue_args(self, value):
        res = check_field(api.ArgumentsField(required=True), value)
        self.assertIsInstance(res, api.ValidationError)
        res = check_field(api.ArgumentsField(nullable=True), value)
        self.assertEqual(res, value)

    @cases([{'account': 'vasya', 'gender': 1}])
    def test_ok_args(self, value):
        res = check_field(api.ArgumentsField(), value)
        self.assertEqual(res, value)


class TestEmailField(unittest.TestCase):

    @cases([1, [1], 'a', '', [], {}])
    def test_bad_email(self, value):
        res = check_field(api.EmailField(), value)
        self.assertIsInstance(res, api.ValidationError)

    @cases([None, ''])
    def test_nullvalue_email(self, value):
        res = check_field(api.EmailField(required=True), value)
        self.assertIsInstance(res, api.ValidationError)
        res = check_field(api.EmailField(nullable=True), value)
        self.assertEqual(res, value)

    @cases(['opex23@inbox.ru', 'v@mail.ru'])
    def test_email_field_ok_email(self, value):
        res = check_field(api.EmailField(), value)
        self.assertEqual(res, value)


class TestPhoneField(unittest.TestCase):

    @cases([1, [1], 'a', '', [], {}, 'a'*11, '7'+'8'*11, '8'*11,
            89151950018, 123, 789, 791519511177])
    def test_bad_phone(self, value):
        res = check_field(api.PhoneField(), value)
        self.assertIsInstance(res, api.ValidationError)

    @cases([None, ''])
    def test_nullvalue_phone(self, value):
        res = check_field(api.PhoneField(required=True), value)
        self.assertIsInstance(res, api.ValidationError)
        res = check_field(api.PhoneField(nullable=True), value)
        self.assertEqual(res, value)

    @cases([79151950018, '79151950018'])
    def test_ok_phone(self, value):
        res = check_field(api.PhoneField(), value)
        self.assertEqual(res, str(value))


class TestDateField(unittest.TestCase):

    @cases([1, [1], 'a', '', [], {}, '2014.01.01', '33.01.2014', '01.01.001',
            '01.32.2014', '12.20.2014'])
    def test_bad_date(self, value):
        res = check_field(api.DateField(), value)
        self.assertIsInstance(res, api.ValidationError)

    @cases([None, ''])
    def test_nullable_date(self, value):
        res = check_field(api.DateField(required=True), value)
        self.assertIsInstance(res, api.ValidationError)
        res = check_field(api.DateField(nullable=True), value)
        self.assertEqual(res, value)

    @cases(['01.01.2014', '30.12.2018'])
    def test_ok_date(self, value):
        res = check_field(api.DateField(), value)
        self.assertEqual(res, datetime.strptime(value, '%d.%m.%Y'))


class TestBirthDayField(unittest.TestCase):

    @cases(['01.11.1948', '01.01.1900', '01.01.2020'])
    def test_bad_birthday(self, value):
        res = check_field(api.BirthDayField(), value)
        self.assertIsInstance(res, api.ValidationError)

    @cases(['01.10.1991', '13.12.2018'])
    def test_ok_birthday(self, value):
        res = check_field(api.BirthDayField(), value)
        self.assertEqual(res, datetime.strptime(value, '%d.%m.%Y'))


class TestGenderField(unittest.TestCase):

    @cases([[1], 'a', '', [], {}, 5, -1])
    def test_bad_gender(self, value):
        res = check_field(api.GenderField(), value)
        self.assertIsInstance(res, api.ValidationError)

    @cases([0, 1, 2])
    def test_ok_gender(self, value):
        res = check_field(api.GenderField(), value)
        self.assertEqual(res, value)        


class TestClientIDsField(unittest.TestCase):

    @cases(
        [1, {1: 1}, 'a', {1, 2}, 0, '', [], {}, ['a'], [[1]], [{1: 1}], [(1,)], [[]], [()]])
    def test_bad_clientids(self, value):
        res = check_field(api.ClientIDsField(), value)
        self.assertIsInstance(res, api.ValidationError)

    @cases([None, []])
    def test_nullable_clientids(self, value):
        res = check_field(api.ClientIDsField(required=True), value)
        self.assertIsInstance(res, api.ValidationError)
        res = check_field(api.ClientIDsField(nullable=True), value)
        self.assertEqual(res, value)

    @cases([[1], [1, 2]])
    def test_ok_clientids(self, value):
        res = check_field(api.ClientIDsField(), value)
        self.assertEqual(res, value)


if __name__ == "__main__":
    unittest.main()
