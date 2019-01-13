#!/usr/bin/env python
# -*- coding: utf-8 -*-

import abc
import json
import datetime
import logging
import hashlib
import uuid
import re
import os
import scoring
import argparse
import configparser
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from store import Storage

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

config = {
    "LOGGING_TO_FILE": None,
    "LOGGING_LEVEL": logging.DEBUG,
    "PORT": 8080,
    "STORE_PORT": 6379,
    "STORE_URL": 'localhost',
    "NUMBER_DB": 0,
    "NUM_RECONNECT": 10,
    "TIMEOUT": 2,
}


def parse_config(default_config, path):
    priority_config = configparser.ConfigParser()
    priority_config.read(path)
    if priority_config.sections():
        priority_config = dict(priority_config.items('Config_api'))
        for item in priority_config.items():
            if item[1] == 'DEBUG':
                priority_config[item[0]] = logging.DEBUG
            if item[1] == 'INFO':
                priority_config[item[0]] = logging.INFO
            if item[1] == 'ERROR':
                priority_config[item[0]] = logging.ERROR
            if item[1].isdigit():
                priority_config[item[0]] = int(item[1])
            default_config[item[0].upper()] = priority_config[item[0]]
    return default_config


class ValidationError(Exception):
    pass


class Field(object):
    __metaclass__ = abc.ABCMeta
    empty_values = ('', [], {})

    def __init__(self, nullable=False, required=False):
        self.required = required
        self.nullable = nullable

    @abc.abstractmethod
    def check(self, value):
        if (self.required and value is None) or (not self.nullable and value in Field.empty_values):
            raise ValidationError('{} is invalid.'
                                  ' Option required/nullable is incorrect!'.format(self.__class__.__name__))
        return value


class CharField(Field):

    def __init__(self, max_length=255, nullable=False, required=False):
        super(CharField, self).__init__(nullable, required)
        self.max_length = max_length

    def check(self, value):
        value = super(CharField, self).check(value)
        if value is not None and not (isinstance(value, (str, unicode)) and len(value) <= self.max_length):
            raise ValidationError('{} is invalid!'.format(self.__class__.__name__))
        return value


class ArgumentsField(Field):

    def check(self, value):
        value = super(ArgumentsField, self).check(value)
        if value is not None and not isinstance(value, dict):
            raise ValidationError('{} is invalid!'.format(self.__class__.__name__))
        return value


class EmailField(CharField):

    def check(self, value):
        value = super(EmailField, self).check(value)
        if value is not None and not (isinstance(value, (int, str, unicode)) and (value == '' or '@' in value)):
            raise ValidationError('{} is invalid!'.format(self.__class__.__name__))
        return value


class PhoneField(Field):
    max_length = 11

    def check(self, value):
        value = super(PhoneField, self).check(value)
        if value is not None:
            value = str(value)
            if not (isinstance(value, (int, str, unicode)) and
                    (value == '' or (re.match(r'\d{11}$', str(value)) and
                                     len(str(value)) == PhoneField.max_length and str(value)[0] == '7'))):
                raise ValidationError('{} is invalid!'.format(self.__class__.__name__))
        return value


class DateField(Field):

    def check(self, value):
        value = super(DateField, self).check(value)
        if isinstance(value, (str, unicode)) or value is None:
            if value is not None and len(value) > 0:
                try:
                    value = datetime.datetime.strptime(value, '%d.%m.%Y')
                except ValueError:
                    raise ValidationError('{} is invalid!'.format(self.__class__.__name__))
        else:
            raise ValidationError('{} is invalid!'.format(self.__class__.__name__))
        return value


class BirthDayField(DateField):

    def check(self, value):
        value = super(BirthDayField, self).check(value)
        if value is not None:
            delta = datetime.datetime.today() - value
            if not 0 < delta.days <= 365 * 70:
                raise ValidationError('{} is invalid!'.format(self.__class__.__name__))
        return value


class GenderField(Field):

    def check(self, value):
        value = super(GenderField, self).check(value)
        if value is not None and not (value in (0, 1, 2)):
            raise ValidationError('{} is invalid!'.format(self.__class__.__name__))
        return value


class ClientIDsField(Field):

    def check(self, value):
        value = super(ClientIDsField, self).check(value)
        if value is not None and not (isinstance(value, list) and all(isinstance(i, int) for i in value)):
            raise ValidationError('{} is invalid!'.format(self.__class__.__name__))
        return value


class Request(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, **kwargs):
        for key in kwargs:
            self.__setattr__(key, kwargs[key])
        self.invalid_fields = []
        self.error_message = None

    def is_valid(self):
        for key, cls in self.__class__.__dict__.items():
            if not isinstance(cls, Field):
                continue
            value = getattr(self, key) if key in self.__dict__ else None
            try:
                self.__setattr__(key, cls.check(value))
            except ValidationError:
                self.invalid_fields.append(key)
        if self.invalid_fields:
            self.error_message = '({0}) this argument(s) is bad'.format(', '.join(self.invalid_fields))
        return False if self.invalid_fields else True


class ClientsInterestsRequest(Request):
    client_ids = ClientIDsField(required=True, nullable=False)
    date = DateField(required=False, nullable=True)


class OnlineScoreRequest(Request):
    first_name = CharField(required=False, nullable=True)
    last_name = CharField(required=False, nullable=True)
    email = EmailField(required=False, nullable=True)
    phone = PhoneField(required=False, nullable=True)
    birthday = BirthDayField(required=False, nullable=True)
    gender = GenderField(required=False, nullable=True)

    def is_valid(self):
        if not super(OnlineScoreRequest, self).is_valid():
            return False
        for i, j in (('phone', 'email'), ('first_name', 'last_name'), ('gender', 'birthday')):
            if getattr(self, i) is not None and getattr(self, j) is not None:
                return True
        self.error_message = ('Request is bad! At least one pair of fields from {(phone, email), '
                              '(first_name, last_name), (gender, birthday)}  should be not empty!')
        return False


class MethodRequest(Request):
    account = CharField(required=False, nullable=True)
    login = CharField(required=True, nullable=True)
    token = CharField(required=True, nullable=True)
    arguments = ArgumentsField(required=True, nullable=True)
    method = CharField(required=True, nullable=True)

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


def clients_interests(req, context, storage):
    response, code = {}, OK
    method = ClientsInterestsRequest(**req.arguments)
    if not method.is_valid():
        return method.error_message, INVALID_REQUEST
    context['nclients'] = len(method.client_ids)
    for i in method.client_ids:
        response[i] = scoring.get_interests(storage, i)
    return response, code


def online_score(req, context, storage):
    response, code = {}, OK
    method = OnlineScoreRequest(**req.arguments)
    if not method.is_valid():
        return method.error_message, INVALID_REQUEST
    context['has'] = req.arguments.keys()
    arguments = {}
    for i in req.arguments.keys():
        arguments[i] = getattr(method, i)
    response['score'] = 42 if req.is_admin else scoring.get_score(storage, **arguments)
    return response, code


def method_handler(request, ctx, store):
    methods = dict(clients_interests=clients_interests, online_score=online_score)
    request = MethodRequest(**request['body'])
    if not request.is_valid():
        return request.error_message, INVALID_REQUEST
    if not check_auth(request):
        return 'Forbidden', FORBIDDEN
    try:
        return methods[request.method](request, ctx, store)
    except KeyError:
        return 'No such method {}!'.format(request.method), INVALID_REQUEST


class MainHTTPHandler(BaseHTTPRequestHandler):
    router = {
        "method": method_handler
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
            logging.exception("Could not read data!")
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
    parser_config = argparse.ArgumentParser()
    parser_config.add_argument('-c', '--config',
                               default="{}/config_api".format(os.path.dirname(os.path.abspath(__file__))))
    path_config = parser_config.parse_args()  # path_config.config -> path to config file
    try:
        config = parse_config(config, path_config.config)
    except Exception:
        raise Exception("Bad config!")
    logging.basicConfig(filename=config['LOGGING_TO_FILE'], level=config['LOGGING_LEVEL'],
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    MainHTTPHandler.store = Storage(host=config['STORE_URL'], port=config['STORE_PORT'], db=config['NUMBER_DB'],
                                    num_reconnect=config['NUM_RECONNECT'], timeout=config['TIMEOUT'])
    server = HTTPServer(("localhost", config['PORT']), MainHTTPHandler)
    logging.info("Starting server at %s" % config['PORT'])
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
