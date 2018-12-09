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
NUM_CONNECTIONS = 100


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
        self.thread = threading.current_thread().name

    def read_all(self):
        data = b''
        while True:
            self.sock.settimeout(TIMEOUT)
            buf = self.sock.recv(1024)
            data += buf
            if not buf or b'\r\n\r\n' in data:
                break
        data = data.decode('utf-8')
        return data

    def run(self):
        try:
            self.handler()
            while self.keep_alive:
                self.handler()
        except Exception as e:
            self.send_response(INTERNAL_ERROR)
            logging.info('Process: {0}, thread: {1} -> ERROR: {2}\n'
                         'Response code: {3}'.format(self.process, self.thread, e, INTERNAL_ERROR))
        finally:
            self.finish()

    def handler(self):
        try:
            request = self.read_all()
        except socket.error:
            self.keep_alive = False
            return
        if not request:
            return self.send_response(BAD_REQUEST)
        code = self.parse_request(request)
        if code != OK:
            return self.send_response(code)
        if self.method.upper() == 'GET':
            return self.send_response(self.do_GET())
        else:
            return self.send_response(self.do_HEAD())

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

    def do_GET(self):
        code = self.set_response_headers()
        return self.set_response_body() if code == OK else code

    def do_HEAD(self):
        return self.set_response_headers()

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

    def finish(self):
        self.sock.close()
        logging.debug('Process: {0}, thread: {1} -> The HttpHandler is closed.'.format(self.process, self.thread))


class WebServer:

    def __init__(self, host='localhost', port=8080, document_root='DOCUMENT_ROOT', http_handler=HttpHandler):
        self.host = host
        self.port = port
        self.document_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), document_root)
        self.http_handler = http_handler
        self.process = multiprocessing.current_process().name
        self.socket = None

    def create_connection(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(NUM_CONNECTIONS)

    def serve_forever(self):
        self.create_connection()
        logging.debug('Connection is created: '
                      'host: {0} | port: {1} | root_dir: {2}'.format(self.host, self.port, self.document_root))
        while True:
            try:
                conn, addr = self.socket.accept()
                logging.debug('Connected: {}'.format(addr))
                request = self.http_handler(conn, addr, self.document_root)
                thread = threading.Thread(target=request.run())
                thread.daemon = True
                thread.start()
            except socket.error as e:
                logging.debug('Process: {0} -> ERROR: {1}'.format(self.process, e))
                self.server_close()

    def server_close(self):
        logging.debug('Process: {0} -> server {1} is closed!'.format(self.process, SERVER_NAME))
        self.socket.close()
