#!/usr/bin/env python3

import socket
import os
import threading
import multiprocessing
import mimetypes
import logging

from datetime import datetime
from urllib.parse import urlparse, unquote

OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
METHOD_NOT_ALLOWED = 405
INTERNAL_ERROR = 500

RESPONSE_CODES = {
    OK: 'OK',
    FORBIDDEN: 'Forbidden',
    NOT_FOUND: 'Not found',
    METHOD_NOT_ALLOWED: 'Method not allowed',
    INTERNAL_ERROR: 'Internal Server Error',
    BAD_REQUEST: 'Bad request',
    }

ALLOWED_METHODS = ('GET', 'HEAD')
ALLOWED_CONTENT_TYPES = (
    'text/html',
    'text/css',
    'text/plain',
    'text/javascript',
    'image/jpeg',
    'image/png',
    'image/gif',
    'application/x-shockwave-flash',
    'application/javascript'
    )

SERVER_NAME = 'OTUServer'
TIMEOUT = 5
NUM_CONNECTIONS = 1000


class HttpHandler:
    def __init__(self, sock, addr, document_root):
        self.sock = sock
        self.client_address = addr
        self.document_root = document_root
        self.response_headers = {}
        self.request_headers = {}
        self.response_body = b''
        self.keep_alive = False
        self.method = None
        self.response_path = ''
        self.protocol = None
        self.process = multiprocessing.current_process().name
        self.pid = os.getpid()
        self.thread = threading.current_thread().name

    def read_all(self):
        data = b''
        self.sock.settimeout(TIMEOUT)
        while True:
            buf = self.sock.recv(1024)
            data += buf
            if not buf or b'\r\n\r\n' in data:
                break
        data = data.decode('utf-8')
        return data

    def run(self):
        logging.debug('process: [name: {0} PID: {1}], thread: {2} -> Start run for request: {3}'.format(
            self.process, self.pid, self.thread, self.client_address))
        try:
            self.handler()
            while self.keep_alive:
                self.response_headers = {}
                self.request_headers = {}
                self.response_body = b''
                self.keep_alive = False
                self.handler()
        except Exception:
            self.send_response(INTERNAL_ERROR)
            logging.exception('process: [name: {0} PID: {1}], thread: {2} -> '
                              'response code: {3} ERROR: '.format(self.process, self.pid, self.thread, INTERNAL_ERROR))
        finally:
            self.finish()

    def handler(self):
        try:
            request = self.read_all()
        except socket.error:
            self.keep_alive = False
            logging.exception('process: [name: {0} PID: {1}], thread: {2} -> ERROR:'.format(self.process, self.pid,
                                                                                            self.thread))
            return
        if not request:
            return self.send_response(BAD_REQUEST)
        logging.debug('process: [name: {0} PID: {1}], thread: {2} -> read_all: OK'.format(self.process, self.pid,
                                                                                          self.thread))
        code = self.parse_request(request)
        logging.debug('process: [name: {0} PID: {1}], thread: {2} -> parse_request: OK, code: {3}'.format(
            self.process, self.pid, self.thread, code))
        if code != OK:
            return self.send_response(code)
        code = self.set_response_headers()
        logging.debug('process: [name: {0} PID: {1}], thread: {2} -> set_response_headers: OK, code: {2}'.format(
            self.process, self.pid, self.thread, code))
        if self.method.upper() == 'GET':
            return self.send_response(self.set_response_body() if code == OK else code)
        else:
            return self.send_response(code)

    def parse_request(self, data):
        request_lines = data.split('\r\n')
        first_string = request_lines[0].split()
        if not len(first_string) == 3:
            return METHOD_NOT_ALLOWED
        self.method, url, self.protocol = first_string
        if self.method.upper() not in ALLOWED_METHODS:
            return METHOD_NOT_ALLOWED
        parsed_url = urlparse(url)
        self.response_path = unquote(parsed_url.path).strip('/')
        self.response_path = os.path.join(self.document_root, self.response_path)
        self.response_path = os.path.realpath(self.response_path)
        if not self.response_path.startswith(self.document_root):
            return FORBIDDEN
        for i in range(1, len(request_lines) - 2):
            key, value = request_lines[i].split(':', 1)
            self.request_headers[key.lower()] = value.strip()
        return OK

    def set_header(self, key, value):
        self.response_headers[key] = value
        if key == 'Connection':
            self.keep_alive = True if value.lower() == 'keep-alive' else False

    def set_response_headers(self):
        if 'connection' in self.request_headers.keys():
            self.set_header('Connection', self.request_headers['connection'])
        if os.path.isdir(self.response_path):
            self.response_path = os.path.join(self.response_path, 'index.html')
            self.set_header('Content-Type', 'text/html')
            try:
                size = os.path.getsize(self.response_path)
            except os.error:
                return NOT_FOUND
            self.set_header('Content-Length', str(size))
            return OK
        elif os.path.isfile(self.response_path):
            m_type = mimetypes.guess_type(self.response_path)[0]
            if m_type not in ALLOWED_CONTENT_TYPES:
                return METHOD_NOT_ALLOWED
            try:
                size = os.path.getsize(self.response_path)
            except os.error:
                return METHOD_NOT_ALLOWED
            self.set_header('Content-Type', '{}'.format(m_type))
            self.set_header('Content-Length', str(size))
            return OK
        else:
            return NOT_FOUND

    def set_response_body(self):
        with open(self.response_path, 'rb') as file:
            self.response_body = file.read(int(self.response_headers['Content-Length']))
        return OK

    def send_response(self, code):
        answer = 'HTTP/1.1 {0} {1}\r\n'.format(str(code), RESPONSE_CODES[code])
        self.set_header('Date', datetime.strftime(datetime.today(), '%Y.%m.%d %H:%M:%S'))
        self.set_header('Server', SERVER_NAME)
        if code != OK:
            self.set_header('Connection', 'close')
            self.keep_alive = False
            self.set_header('Content-Type', 'text/html')
            self.set_header('Content-Length', '0')
        answer = answer + '\r\n'.join(['{0}: {1}'.format(item[0], item[1]) for item in self.response_headers.items()])
        answer += '\r\n\r\n'
        answer = bytes(answer, 'utf-8')
        if self.response_body:
            answer += self.response_body
        self.sock.sendall(answer)
        logging.info(
            'Process: {0}, thread: {1} -> address: {2} | request: "{3} {4} {5}" | code: {6} {7} | size: {8}'.format(
                self.process, self.thread, self.client_address[0], self.method, self.response_path,
                self.protocol, code, RESPONSE_CODES[code], self.response_headers['Content-Length']))
                     
    def finish(self):
        self.sock.close()
        logging.debug('Process: {0}, thread: {1} -> The HttpHandler is closed.'.format(self.process, self.thread))


class WebServer:

    def __init__(self, host='localhost', port=80, document_root='DOCUMENT_ROOT', http_handler=HttpHandler):
        self.host = host
        self.port = port
        self.document_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), document_root)
        if not os.path.isdir(self.document_root):
            os.makedirs(self.document_root)
        self.http_handler = http_handler
        self.process = multiprocessing.current_process().name
        self.pid = os.getpid()
        self.socket = None

    def create_connection(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(NUM_CONNECTIONS)

    def do_request(self, sock, address):
        request = self.http_handler(sock, address, self.document_root)
        request.run()

    def serve_forever(self):
        try:
            self.create_connection()
        except socket.error:
            logging.exception('process: [name: {0} PID: {1}] -> Unexpected socket.error!'.format(self.process,
                                                                                                 self.pid))
            return
        while True:
            try:
                conn, addr = self.socket.accept()
                thread = threading.Thread(target=self.do_request, args=(conn, addr))
                thread.daemon = True
                thread.start()
            except socket.error:
                logging.exception('process: [name: {0} PID: {1}] -> ERROR:\n'.format(self.process, self.pid))
                self.server_close()
                break

    def server_close(self):
        logging.debug('process: [name: {0} PID: {1}] -> server {2} is stopped!'.format(self.process, self.pid,
                                                                                       SERVER_NAME))
        self.socket.close()
