from io import BytesIO
from os import path
from unittest import TestCase

from cimbar.encode.rss import reed_solomon_stream


CIMBAR_ROOT = path.abspath(path.join(path.dirname(path.realpath(__file__)), '..'))


class ReedSolomonStreamTest(TestCase):
    def test_encode_decode(self):
        s = b'0123456789'*12 + b'01234'
        expected_rs_code = (
            b'\x1a\xd0\xc75-\x08\xde\x9a\xdc\x9a\x17_\xa2\xf6\x15\x8b\x0e\xb2\xd4\xbb\x19\xe6:\x88\x1b\xee\x92\xd7N\xab'
        )

        inbuff = BytesIO(s*2)
        outbuff = BytesIO()
        with reed_solomon_stream(inbuff, 30, 155) as reed_read, reed_solomon_stream(outbuff, 30, 155, mode='write') as reed_write:
            b = reed_read.read(125)
            self.assertEqual(s + expected_rs_code, b)
            reed_write.write(b)

            outbuff.seek(0)
            self.assertEqual(s, outbuff.read())

