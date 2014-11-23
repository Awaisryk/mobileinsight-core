# -*- coding: utf-8 -*-
"""
hdlc_parser.py
Define hdlc_parser class that deals with HDLC frames in the raw logs produced by monitor.

Author: Jiayao Li
"""

import struct
import crcmod
import binascii

class hdlc_parser:
    """
    This class takes fragmented HDLC encapsulated data, decode its frame 
    structure and return the clean HDLC frame.
    """
    def __init__(self):
        self._remain_frames = []
        self._incomplete = None

    def feed_binary(self, ts, binary):
        b_lst = binary.split("\x7e")
        print repr(b_lst)
        for i in range(len(b_lst)):
            b = b_lst[i]
            if i == len(b_lst) - 1:
                if not b:
                    continue
                # incomplete frame 
                if self._incomplete:
                    self._incomplete[1] += b
                else:
                    self._incomplete = [None, None]
                    self._incomplete[0] = ts
                    self._incomplete[1] = b
            else:
                if self._incomplete:
                    this_ts = self._incomplete[0]
                    this_fr = self._incomplete[1] + b
                    self._incomplete = None
                else:
                    this_ts = ts
                    this_fr = b
                if not this_fr:
                    continue
                payld, fcs = self._clean_escape(this_fr)
                crc_correct = self._check_crc(payld, fcs)
                self._remain_frames.append(tuple([this_ts, payld, fcs, crc_correct]))

    def _clean_escape(self, frame_binary):
        payld = []
        esc = False
        for c in frame_binary[0:-2]:
            if esc:
                orig_c = chr(ord(c) ^ 0x20)
                print '7d %s ==> %s' % (binascii.b2a_hex(c), binascii.b2a_hex(orig_c))
                payld.append(orig_c)
                esc = False
            else:
                if c == '\x7d':
                    esc = True
                else:
                    payld.append(c)
        payld = ''.join(payld)
        fcs = struct.unpack("<H", frame_binary[-2:])[0]   # unsigned short
        return payld, fcs

    def _check_crc(self, payld, fcs):
        crc16 = crcmod.predefined.Crc('x-25')
        for c in payld:
            crc16.update(c)
        calc_crc = struct.unpack(">H", crc16.digest())[0]
        print 'Calc %s, FCS %s' % (hex(calc_crc), hex(fcs))
        return calc_crc == fcs

    def __iter__(self):
        return self

    def next(self):
        if len(self._remain_frames) > 0:
            t, fr, fcs, crc_correct = self._remain_frames.pop(0)
            return t, fr, fcs, crc_correct
        else:
            raise StopIteration()


if __name__ == '__main__':
    b = "7d 5d 02 88 13 a5 13 c3 40 7e".replace(" ", "")
    b += "7d 5d 02 7c 15 8c 15 c0 02 7e".replace(" ", "")
    b = binascii.a2b_hex(b)

    parser = hdlc_parser()
    parser.feed_binary(0.0, b[0:5])
    parser.feed_binary(0.5, b[5:7])
    parser.feed_binary(1.0, b[7:])
    for t, fr, fcs, crc_correct in parser:
        print t, binascii.b2a_hex(fr), hex(fcs), crc_correct