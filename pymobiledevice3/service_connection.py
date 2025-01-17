import logging
import plistlib
import ssl
import struct
from re import sub

import IPython
from pygments import highlight, lexers, formatters

from pymobiledevice3 import usbmux
from pymobiledevice3.exceptions import ConnectionFailedError, PyMobileDevice3Exception

SHELL_USAGE = """
# This shell allows you to communicate directly with every service layer behind the lockdownd daemon.

# For example, you can do the following:
client.send_plist({"Command": "DoSomething"})

# and view the reply
print(client.recv_plist())

# or just send raw message
client.send(b"hello")

# and view the result
print(client.recvall(20))
"""


class ServiceConnection(object):
    def __init__(self, socket):
        self.logger = logging.getLogger(__name__)
        self.socket = socket

    @staticmethod
    def create(udid, port):
        target_device = None
        while target_device is None:
            matching_devices = [device for device in usbmux.list_devices() if device.serial == udid]
            if len(matching_devices) == 1:
                target_device = matching_devices[0]
                break

        try:
            socket = target_device.connect(port)
        except usbmux.MuxException:
            raise ConnectionFailedError(f'Connection to device port {port} failed')

        return ServiceConnection(socket)

    def setblocking(self, blocking: bool):
        self.socket.setblocking(blocking)

    def close(self):
        self.socket.close()

    def recv(self, length=4096):
        """ socket.recv() normal behavior. attempt to receive a single chunk """
        return self.socket.recv(length)

    def sendall(self, data):
        self.socket.sendall(data)

    def send_recv_plist(self, data, endianity='>', fmt=plistlib.FMT_XML):
        self.send_plist(data, endianity=endianity, fmt=fmt)
        return self.recv_plist(endianity=endianity)

    def recvall(self, size):
        data = b''
        while len(data) < size:
            chunk = self.recv(size - len(data))
            if chunk is None or len(chunk) == 0:
                raise ConnectionAbortedError()
            data += chunk
        return data

    def recv_prefixed(self, endianity='>'):
        """ receive a data block prefixed with a u32 length field """
        size = self.recvall(4)
        if not size or len(size) != 4:
            return
        size = struct.unpack(endianity + 'L', size)[0]
        return self.recvall(size)

    def send_prefixed(self, data):
        """ send a data block prefixed with a u32 length field """
        if isinstance(data, str):
            data = data.encode()
        hdr = struct.pack('>L', len(data))
        msg = b''.join([hdr, data])
        return self.sendall(msg)

    def recv_plist(self, endianity='>'):
        payload = self.recv_prefixed(endianity=endianity)
        if not payload:
            return
        bplist_header = b'bplist00'
        xml_header = b'<?xml'
        if payload.startswith(bplist_header):
            return plistlib.loads(payload)
        elif payload.startswith(xml_header):
            # HAX lockdown HardwarePlatform with null bytes
            payload = sub(r'[^\w<>\/ \-_0-9\"\'\\=\.\?\!\+]+', '', payload.decode('utf-8')).encode('utf-8')
            return plistlib.loads(payload)
        else:
            raise PyMobileDevice3Exception(f'recv_plist invalid data: {payload[:100].hex()}')

    def send_plist(self, d, endianity='>', fmt=plistlib.FMT_XML):
        payload = plistlib.dumps(d, fmt=fmt)
        message = struct.pack(endianity + 'L', len(payload))
        return self.sendall(message + payload)

    def ssl_start(self, keyfile, certfile):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.set_ciphers('AES256-SHA')
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.load_cert_chain(certfile, keyfile)
        self.socket = context.wrap_socket(self.socket)

    def shell(self):
        IPython.embed(
            header=highlight(SHELL_USAGE, lexers.PythonLexer(), formatters.TerminalTrueColorFormatter(style='native')),
            user_ns={
                'client': self,
            })
