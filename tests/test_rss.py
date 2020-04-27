from io import BytesIO
from os import path
from unittest import TestCase

from cimbar.encode.rss import reed_solomon_stream


CIMBAR_ROOT = path.abspath(path.join(path.dirname(path.realpath(__file__)), '..'))


class ReedSolomonStreamTest(TestCase):
    def test_encode_decode(self):
        s = b'0123456789'*14 + b'abcde'
        expected_rs_code = b's\x9a\x7f\xa7\xe9#\xc4\xbc\xc1#'

        inbuff = BytesIO(s)
        outbuff = BytesIO()
        with reed_solomon_stream(inbuff) as reed_read, reed_solomon_stream(outbuff, mode='write') as reed_write:
            b = reed_read.read(145)
            self.assertEqual(s + expected_rs_code, b)
            reed_write.write(b)

            outbuff.seek(0)
            self.assertEqual(s, outbuff.read())

