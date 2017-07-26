#!/usr/bin/env python

import sys
import bisect
from twisted.internet.endpoints import clientFromString
from twisted.internet import protocol
from twisted.internet import reactor
from twisted.internet.protocol import Factory
from twisted.python.log import startLogging
import json
import pysrt


class MpvVrate(protocol.Protocol):
    exp = []
    buf = b''
    pos = 0
    cur_speed = None
    subf = None

    def _send_cmd(self, cmd):
        cmd = json.dumps({"command": cmd}).encode('ascii') + b'\n'
        # print('> CMD', cmd)
        self.transport.write(cmd)

    def get_pos(self):
        self._send_cmd(["get_property", "playback-time"])
        self.exp.append('getpos')

    def get_tdiff(self):
        pass

    def get_trackdata(self):
        self._send_cmd(["get_property", "track-list"])
        self.exp.append('trackdata')
        pass

    def get_subfname(self, idx):
        self._send_cmd(["get_property", "track-list/%d/external-filename" % idx])
        self.exp.append('subfname')
        pass

    def get_speed(self):
        self._send_cmd(["get_property", "speed"])
        self.exp.append('getspeed')

    def set_speed(self, speed):
        self._send_cmd(["set_property", "speed", speed])
        self.cur_speed = speed

    def connectionMade(self):
        # print("made")
        self.get_pos()
        self.get_speed()
        self.get_trackdata()

    def dataReceived(self, data):
        # print("data", data)
        try:
            idx = data.index(b'\n')
        except IndexError:
            self.buf += data
            return
        d = self.buf + data[:idx]
        remain = data[idx+1:]
        self.buf = b''

        j = json.loads(d)
        # print(j)
        self.handle_json(j)
        if remain:
            self.dataReceived(remain)

    def handle_json(self, j):
        if 'event' in j:
            # print("event", j)
            return
        elif not self.exp:
            return
        exp = self.exp.pop(0)
        if 'error' in j and j['error'] != 'success':
            print("error", j)
            return
        if exp == 'getspeed':
            self.cur_speed = j['data']
            print(self.cur_speed, 'speed')
        if exp == 'getpos':
            if 'data' not in j:
                print("getpos data expected")
                return
            self.pos = j['data'] * 1000
            # print("pos", self.pos)
            if not self.subf:
                return
            in_sub, towait = self.subf.next_sub(self.pos)
            if in_sub < 0:
                return  # no more subs
            if in_sub and self.cur_speed != 1.0:
                print("In subtitle, reduce speed")
                self.set_speed(1.0)
            elif (not in_sub) and self.cur_speed != 2.0:
                print("Not in subtitle, increase speed")
                self.set_speed(2.0)
            if towait/self.cur_speed > 1000:
                towait = 1000
            print("wait", towait / 1000)
            reactor.callLater(towait / 1000, self.get_pos)
        elif exp == 'trackdata':
            for idx, d in enumerate(j['data']):
                if d['type'] == 'sub' and d['external'] is True:
                    self.get_subfname(idx)
                    break
        elif exp == 'subfname':
            fname = j['data']
            print("Using subtitles file %s." % fname)
            self.subf = SRT(fname)
            self.get_pos()


class SRT(object):
    def __init__(self, fname):
        self.subf = pysrt.open(fname)
        self.startlist = []
        self.endlist = []
        for s in self.subf:
            self.startlist.append(s.start.ordinal)
            self.endlist.append(s.end.ordinal)

        # XXX merge?

        # print(self.next_sub(0))
        # print(self.next_sub(3327262))
        # print(self.next_sub(3327264))

        # print(self.next_sub(999999999))
        # API
        # self.subf.at(1234)
        # self.subf[0].start.ordinal  # ms
        # self.subf[0].end.ordinal  # ms
        # self.subf[0].duration  # ms

    def next_sub(self, pos):
        start_idx = bisect.bisect(self.startlist, pos)
        end_idx = bisect.bisect(self.endlist, pos)
        if start_idx != end_idx:
            in_sub = True
            npos = self.endlist[end_idx]
        else:
            if start_idx == len(self.startlist):
                npos = -1
            else:
                in_sub = False
                npos = self.startlist[start_idx]
        delta = npos - pos
        return in_sub, delta


class MPVFactory(Factory):
    def buildProtocol(self, addr):
        return MpvVrate()


startLogging(sys.stdout)

endpoint = clientFromString(reactor, "unix:path=/tmp/mpv-socket")
# endpoint = clientFromString(reactor, "tcp:127.0.0.1:9000")
endpoint.connect(MPVFactory())

reactor.run()


# class vrate(object):

#     def __init__(self):
#         self.client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
#         self.client.setblocking(False)
#         try:
#             self.client.connect("/tmp/mpv-socket")
#         except socket.error as e:
#             print("Error while connecting to mpv socket")
#             print(e)
#             sys.exit(1)

#     def _build_cmd(self, cmd):
#         return json.dumps({"command": cmd}).encode('ascii')

#     def get_pos(self):
#         cmdtxt = self._build_cmd(["get_property", "playback-time"])
#         print(cmdtxt)
#         print(self.client.sendall(cmdtxt))
#         while True:
#             r, w, e = select.select([self.client], [], [])
#             if r:
#                 print(r)
#                 self.client.recv(2)
#                 break
#         print('recv')
#         print(self.client.recv(4))


# if __name__ == "__main__":
#     vr = vrate()
#     vr.get_pos()
