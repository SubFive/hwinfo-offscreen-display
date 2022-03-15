from pprint import pprint
import socket
import time
import struct
import datetime
import re
from collections import defaultdict

from http.server import SimpleHTTPRequestHandler
import socketserver
import json

HWINFOHOST = "127.0.0.1"
HWINFOPORT = 27007

_handshake = bytearray([
  0x43, 0x52, 0x57, 0x48, 0x01, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
])

_accept = bytearray([
  0x43, 0x52, 0x57, 0x48, 0x02, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
])


def handshake(_socket):
    _socket.sendall(_handshake)
    data = _socket.recv(132)
    (len_response,) = struct.unpack('12xi', data[:16])
    _socket.recv(len_response)

def request_more(_socket):
    _socket.sendall(_accept)
    data = _socket.recv(132)
    (len_response,) = struct.unpack('12xi', data[:16])
    return len_response

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

HEADER_LEN = 60
SECTION_NAME_LEN = 128
SECTION_HEADER_LEN = 8

s.connect((HWINFOHOST, HWINFOPORT))
handshake(s)

def null_term_str(bytess):
    return bytess.decode('latin_1').strip('\0')

def normalize_item_name(name):
    name = name.lower()
    name = name.replace('[', '')
    name = name.replace(']', '')
    name = name.replace('.', '')
    name = name.replace(': ', '.')
    name = name.replace(' #', '')
    name = name.replace(' ', '_')
    name = name.replace('(', '')
    name = name.replace(')', '')

    if name.startswith('gpu0'):
        name = 'gpu0'
    if name.startswith('gpu1'):
        name = 'gpu1'
    if name.startswith('cpu0'):
        name = 'cpu0'
    if name.startswith('cpu1'):
        name = 'cpu1'

    return name

def pull_data():
    incoming_msg_len = request_more(s)

    payload = bytes()

    while len(payload) < incoming_msg_len:
        payload = payload + s.recv(4096)

    header = payload[:HEADER_LEN]
    (
        msgsize,
        timestamp,
        section_len,
        num_sections,
        section_item_len,
        num_section_items
    ) = struct.unpack('8xI12xI8xII4xII4x', header)

    sections = payload[HEADER_LEN:HEADER_LEN+(section_len * num_sections)]
    section_items = payload[HEADER_LEN+(section_len * num_sections):]

    parsed_sections = []
    for i in range(num_sections):
        step = i * section_len
        
        section_bytearray = sections[step : step + (SECTION_NAME_LEN + SECTION_HEADER_LEN)]

        (inscrutable_header, section_name) = struct.unpack('=Q128s', section_bytearray)

        parsed_sections.append(normalize_item_name(null_term_str(section_name)))

    result = {}
    for i in range(num_section_items):
        
        section_item_bytearray = section_items[i * section_item_len: i * section_item_len + section_item_len]

        (
            category,
            section_idx,
            inscrutable_header,
            label,
            unit,
            cur,
            minn,
            maxx,
            avg
        ) = struct.unpack('=III128s128x16sdddd', section_item_bytearray)

        label = null_term_str(label)
        unit = null_term_str(unit)

        result[parsed_sections[section_idx] + '.' + normalize_item_name(label) + '.unit'] = unit
        result[parsed_sections[section_idx] + '.' + normalize_item_name(label) + '.current'] = cur
        result[parsed_sections[section_idx] + '.' + normalize_item_name(label) + '.min'] = minn
        result[parsed_sections[section_idx] + '.' + normalize_item_name(label) + '.max'] = maxx
        result[parsed_sections[section_idx] + '.' + normalize_item_name(label) + '.avg'] = avg

    return result


class MyHttpRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/data':
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(pull_data()).encode('utf-8'))
        else:
            self.path = './index.html'
        
            return SimpleHTTPRequestHandler.do_GET(self)

my_server = None

try:
    handler_object = MyHttpRequestHandler

    PORT = 8000
    my_server = socketserver.TCPServer(("", PORT), handler_object)

    my_server.serve_forever()
except KeyboardInterrupt:
    my_server.server_close()
    s.shutdown(socket.SHUT_RDWR)
    s.close()
    exit(0)