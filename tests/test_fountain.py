from io import BytesIO
from os import path
from unittest import TestCase

from cimbar.fountain.header import fountain_header
from cimbar.fountain.fountain_encoder_stream import fountain_encoder_stream


CIMBAR_ROOT = path.abspath(path.join(path.dirname(path.realpath(__file__)), '..'))



class FountainHeaderTest(TestCase):
    def test_header_encode(self):
        self.assertEqual(b'\x01\x00\x04\x00\x00\x03', bytes(fountain_header(1, 1024, 3)))

    def test_header_decode(self):
        f = fountain_header(b'\x01\x00\x04\x00\x00\x03')
        self.assertEqual(1, f.encode_id)
        self.assertEqual(1024, f.total_size)
        self.assertEqual(3, f.chunk_id)

    def test_header_decode_2(self):
        f = fountain_header(b'\x0a\x07\x08\x09\x00\x00')
        self.assertEqual(10, f.encode_id)
        self.assertEqual(0x070809, f.total_size)
        self.assertEqual(0, f.chunk_id)


class FountainTest(TestCase):
    def test_encode_decode(self):
        self.assertFalse(True)

