#!/usr/bin/env python
# -*- coding: utf-8 -*-

import abc
import json
import datetime
import logging
import hashlib
import uuid
import re
import scoring
from optparse import OptionParser
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


class Field(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, nullable=False, required=False):
        self.required = required
        self.nullable = nullable

    @abc.abstractmethod
    def check(self, value):
        return True if self.nullable else False


class CharField(Field):

    def __init__(self, max_length=255, nullable=False, required=False):
        super(CharField, self).__init__(nullable, required)
        self.max_length = max_length

    def check(self, value):
        ans = False
        if isinstance(value, (str, unicode)):
            if value:
                if len(value) <= self.max_length:
                    ans = True
            else:
                ans = super(CharField, self).check(value)
        return ans


class ArgumentsField(Field):

    def check(self, value):
        ans = False
        if isinstance(value, dict):
            if value:
                ans = True
            else:
                ans = super(ArgumentsField, self).check(value)
        return ans


class EmailField(CharField):

    def check(self, value):
        ans = False
        if super(EmailField, self).check(value) and (value == '' or '@' in value):
            ans = True
        return ans


class PhoneField(Field):

    def __init__(self, nullable=False, required=False):
        super(PhoneField, self).__init__(nullable, required)
        self.max_length = 11

    def check(self, value):
        ans = False
        if isinstance(value, (int, str, unicode)):
            value = str(value)
            if value:
                if re.match(r'\d{11}$', value) and len(value) == self.max_length and value[0] == '7':
                    ans = True
            else:
                ans = super(PhoneField, self).check(value)
        return ans


class DateField(Field):

    def check(self, value):
        ans = False
        if isinstance(value, (str, unicode)):
            if value:
                if re.match(r'\d{2}.\d{2}.\d{4}$', value):
                    ans = True
            else:
                ans = super(DateField, self).check(value)
        return ans


class BirthDayField(DateField):

    def check(self, value):
        ans = False
        if super(BirthDayField, self).check(value):
            if value:
                delta = datetime.datetime.today() - datetime.datetime.strptime(value, '%d.%m.%Y')
                if 0 < delta.days <= 365 * 70:
                    ans = True
            else:
                ans = True
        return ans


class GenderField(Field):

    def check(self, value):
        ans = False
        if value in (0, 1, 2):
            if value:
                ans = True
            else:
                ans = super(GenderField, self).check(value)
        return ans


class ClientIDsField(Field):

    def check(self, value):
        ans = False
        if isinstance(value, list):
            if value:
                if all(isinstance(i, int) for i in value):
                    ans = True
            else:
                ans = super(ClientIDsField, self).check(value)
        return ans


class Request(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, **kwargs):
        for key in kwargs:
            new_key = '_{}'.format(key)
            self.__dict__[new_key] = kwargs[key]

    def is_valid(self):
        invalid_fields = []
        for atr in self.__dict__.keys():
            value = self.__getattribute__(atr)
            instance = self.__getattribute__(atr.lstrip('_'))
            if instance.required and value is None:
                invalid_fields.append(atr.lstrip('_'))
            else:
                if value is not None:
                    if instance.check(value):
                        self.__setattr__(atr.lstrip('_'), value)
                        self.__delattr__(atr)
                    else:
                        invalid_fields.append(atr.lstrip('_'))
                else:  # value = None, required = False
                    self.__setattr__(atr.lstrip('_'), value)
                    self.__delattr__(atr)
        return invalid_fields if invalid_fields else True


class ClientsInterestsRequest(Request):
    client_ids = ClientIDsField(required=True, nullable=False)
    date = DateField(required=False, nullable=True)

    def __init__(self, client_ids=None, date=None):
        super(ClientsInterestsRequest, self).__init__(client_ids=client_ids, date=date)


class OnlineScoreRequest(Request):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def __init__(self, first_name=None, last_name=None, email=None, phone=None, birthday=None, gender=None):
        super(OnlineScoreRequest, self).__init__(first_name=first_name, last_name=last_name, email=email,
                                                 phone=phone, birthday=birthday, gender=gender)

    def is_valid(self):
        invalid_fields = super(OnlineScoreRequest, self).is_valid()
        if invalid_fields is not True:
            return invalid_fields
        invalid_fields = []
        for i, j in (('phone', 'email'), ('first_name', 'last_name'), ('gender', 'birthday')):
            if self.__dict__[i] is not None and self.__dict__[j] is not None:
                return True
            elif self.__dict__[i] is None and self.__dict__[j] is None:
                invalid_fields.append(j)
                invalid_fields.append(i)
            else:
                invalid_fields.append(j) if self.__dict__[i] else invalid_fields.append(i)
        return invalid_fields


class MethodRequest(Request):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=True)

    def __init__(self, account=None, login=None, token=None, arguments=None, method=None):
        super(MethodRequest, self).__init__(account=account, login=login, token=token, arguments=arguments,
                                            method=method)

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


def check_auth(request):
    if request.is_admin:
        digest = hashlib.sha512(datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).hexdigest()
    else:
        digest = hashlib.sha512(request.account + request.login + SALT).hexdigest()
    if digest == request.token:
        return True
    return False


def method_handler(request, ctx, store):
    req = MethodRequest(**request['body'])
    valid = req.is_valid()
    if valid is not True:
        return '({0}) this field(s) is bad'.format(' '.join(valid)), 422
    if not check_auth(req):
        return 'Forbidden', 403
    return req.arguments, req.is_admin


def clients_interests(request, ctx, store):
    response, code = {}, OK
    arguments, admin = method_handler(request, ctx, store)
    if admin in (422, 403):
        return arguments, admin
    method = ClientsInterestsRequest(**arguments)
    valid = method.is_valid()
    if valid is not True:
        return '({0}) this argument(s) is bad'.format(', '.join(valid)), 422
    client_ids = list(method.client_ids)
    ctx['nclients'] = len(client_ids)
    for i in client_ids:
        response[i] = scoring.get_interests(store, None)
    return response, code


def online_score(request, ctx, store):
    response, code = {}, OK
    arguments, admin = method_handler(request, ctx, store)
    if admin in (422, 403):
        return arguments, admin
    method = OnlineScoreRequest(**arguments)
    valid = method.is_valid()
    if valid is not True:
        return '({0}) this argument(s) is empty'.format(', '.join(valid)), 422
    ctx['has'] = arguments.keys()
    if admin:
        response['score'] = 42
    else:
        response['score'] = scoring.get_score(store, **arguments)
    return response, code


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler,
        "online_score": online_score,
        "clients_interests": clients_interests
    }
    store = None

    def get_request_id(self, headers):
        return headers.get('HTTP_X_REQUEST_ID', uuid.uuid4().hex)

    def do_POST(self):
        response, code = {}, OK
        context = {"request_id": self.get_request_id(self.headers)}
        request = None
        try:
            data_string = self.rfile.read(int(self.headers['Content-Length']))
            request = json.loads(data_string)
        except:
            code = BAD_REQUEST

        if request:
            path = self.path.strip("/")
            logging.info("%s: %s %s" % (self.path, data_string, context["request_id"]))
            if path in self.router:
                try:
                    response, code = self.router[path]({"body": request, "headers": self.headers}, context, self.store)
                except Exception as e:
                    logging.exception("Unexpected error: %s" % e)
                    code = INTERNAL_ERROR
            else:
                code = NOT_FOUND

        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if code not in ERRORS:
            r = {"response": response, "code": code}
        else:
            r = {"error": response or ERRORS.get(code, "Unknown Error"), "code": code}
        context.update(r)
        logging.info(context)
        self.wfile.write(json.dumps(r))
        return


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-p", "--port", action="store", type=int, default=8080)
    op.add_option("-l", "--log", action="store", default=None)
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", opts.port), MainHTTPHandler)
    logging.info("Starting server at %s" % opts.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
