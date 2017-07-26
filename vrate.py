#!/usr/bin/env python
import json
import socket
import select
import sys


class vrate(object):

    def __init__(self):
        self.client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.client.setblocking(False)
        try:
            self.client.connect("/tmp/mpv-socket")
        except socket.error as e:
            print("Error while connecting to mpv socket")
            print(e)
            sys.exit(1)

    def _build_cmd(self, cmd):
        return json.dumps({"command": cmd}).encode('ascii')

    def get_pos(self):
        cmdtxt = self._build_cmd(["get_property", "playback-time"])
        print(cmdtxt)
        print(self.client.sendall(cmdtxt))
        while True:
            r, w, e = select.select([self.client], [], [])
            if r:
                print(r)
                self.client.recv(2)
                break
        print('recv')
        print(self.client.recv(4))


if __name__ == "__main__":
    vr = vrate()
    vr.get_pos()
