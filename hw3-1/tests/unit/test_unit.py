import datetime
import unittest
from api import api

from datetime import datetime
from tests.cases import cases


class TestCharField(unittest.TestCase):

    @cases([1, [1], {1: 1}, 'a'*256, 0, '', [], {}])
    def test_bad_char(self, value):
        self.assertRaises(api.ValidationError, api.CharField().check, value)

    @cases([None, ''])
    def test_nullvalue_char(self, value):
        self.assertRaises(api.ValidationError, api.CharField(required=True).check, value)
        res = api.CharField(nullable=True).check(value)
        self.assertEqual(res, value)

    @cases(['otus', 'a'*255])
    def test_ok_char(self, value):
        res = api.CharField().check(value)
        self.assertEqual(res, value)


class TestArgumentField(unittest.TestCase):

    @cases([1, [1], 'a', '', [], {}])
    def test_bad_args(self, value):
        self.assertRaises(api.ValidationError, api.ArgumentsField().check, value)

    @cases([None, {}])
    def test_nullvalue_args(self, value):
        self.assertRaises(api.ValidationError, api.ArgumentsField(required=True).check, value)
        res = api.ArgumentsField(nullable=True).check(value)
        self.assertEqual(res, value)

    @cases([{'account': 'vasya', 'gender': 1}])
    def test_ok_args(self, value):
        res = api.ArgumentsField().check(value)
        self.assertEqual(res, value)


class TestEmailField(unittest.TestCase):

    @cases([1, [1], 'a', '', [], {}])
    def test_bad_email(self, value):
        self.assertRaises(api.ValidationError, api.EmailField().check, value)

    @cases([None, ''])
    def test_nullvalue_email(self, value):
        self.assertRaises(api.ValidationError, api.EmailField(required=True).check, value)
        res = api.EmailField(nullable=True).check(value)
        self.assertEqual(res, value)

    @cases(['opex23@inbox.ru', 'v@mail.ru'])
    def test_email_field_ok_email(self, value):
        res = api.EmailField().check(value)
        self.assertEqual(res, value)


class TestPhoneField(unittest.TestCase):

    @cases([1, [1], 'a', '', [], {}, 'a'*11, '7'+'8'*11, '8'*11,
            89151950018, 123, 789, 791519511177])
    def test_bad_phone(self, value):
        self.assertRaises(api.ValidationError, api.PhoneField().check, value)

    @cases([None, ''])
    def test_nullvalue_phone(self, value):
        self.assertRaises(api.ValidationError, api.PhoneField(required=True).check, value)
        res = api.PhoneField(nullable=True).check(value)
        self.assertEqual(res, value)

    @cases([79151950018, '79151950018'])
    def test_ok_phone(self, value):
        res = api.PhoneField().check(value)
        self.assertEqual(res, str(value))


class TestDateField(unittest.TestCase):

    @cases([1, [1], 'a', '', [], {}, '2014.01.01', '33.01.2014', '01.01.001',
            '01.32.2014', '12.20.2014'])
    def test_bad_date(self, value):
        self.assertRaises(api.ValidationError, api.DateField().check, value)

    @cases([None, ''])
    def test_nullable_date(self, value):
        self.assertRaises(api.ValidationError, api.DateField(required=True).check, value)
        res = api.DateField(nullable=True).check(value)
        self.assertEqual(res, value)

    @cases(['01.01.2014', '30.12.2018'])
    def test_ok_date(self, value):
        res = api.DateField().check(value)
        self.assertEqual(res, datetime.strptime(value, '%d.%m.%Y'))


class TestBirthDayField(unittest.TestCase):

    @cases(['01.11.1948', '01.01.1900', '01.01.2020'])
    def test_bad_birthday(self, value):
        self.assertRaises(api.ValidationError, api.BirthDayField().check, value)

    @cases(['01.10.1991', '13.12.2018'])
    def test_ok_birthday(self, value):
        res = api.BirthDayField().check(value)
        self.assertEqual(res, datetime.strptime(value, '%d.%m.%Y'))


class TestGenderField(unittest.TestCase):

    @cases([[1], 'a', '', [], {}, 5, -1])
    def test_bad_gender(self, value):
        self.assertRaises(api.ValidationError, api.GenderField().check, value)

    @cases([0, 1, 2])
    def test_ok_gender(self, value):
        res = api.GenderField().check(value)
        self.assertEqual(res, value)


class TestClientIDsField(unittest.TestCase):

    @cases(
        [1, {1: 1}, 'a', {1, 2}, 0, '', [], {}, ['a'], [[1]], [{1: 1}], [(1,)], [[]], [()]])
    def test_bad_clientids(self, value):
        self.assertRaises(api.ValidationError, api.ClientIDsField().check, value)

    @cases([None, []])
    def test_nullable_clientids(self, value):
        self.assertRaises(api.ValidationError, api.ClientIDsField(required=True).check, value)
        res = api.ClientIDsField(nullable=True).check(value)
        self.assertEqual(res, value)

    @cases([[1], [1, 2]])
    def test_ok_clientids(self, value):
        res = api.ClientIDsField().check(value)
        self.assertEqual(res, value)


if __name__ == "__main__":
    unittest.main()
