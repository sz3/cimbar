from io import BytesIO
from os import path
from unittest import TestCase

from cimbar.fountain.header import fountain_header
from cimbar.fountain.fountain_decoder_stream import fountain_decoder_stream
from cimbar.fountain.fountain_encoder_stream import fountain_encoder_stream


CIMBAR_ROOT = path.abspath(path.join(path.dirname(path.realpath(__file__)), '..'))
SAMPLE_FILE = path.join(CIMBAR_ROOT, 'LICENSE')


class FountainHeaderTest(TestCase):
    def test_header_encode(self):
        self.assertEqual(b'\x01\x00\x04\x00\x00\x03', bytes(fountain_header(1, 1024, 3)))

    def test_header_decode(self):
        f = fountain_header(b'\x01\x00\x04\x00\x00\x03')
        self.assertEqual(1, f.encode_id)
        self.assertEqual(1024, f.total_size)
        self.assertEqual(3, f.chunk_id)

    def test_header_decode_consistency(self):
        f = fountain_header(b'\x0a\x07\x08\x09\x00\x00')
        self.assertEqual(10, f.encode_id)
        self.assertEqual(0x070809, f.total_size)
        self.assertEqual(0, f.chunk_id)

    def test_header_encode_bigfile(self):
        fe = fountain_header(2, 0x1FFFFFF, 3)
        self.assertEqual(b'\x82\xff\xff\xff\x00\x03', bytes(fe))

    def test_header_decode_bigfile(self):
        f = fountain_header(b'\x81\x07\x08\x09\x00\x00')
        self.assertEqual(1, f.encode_id)
        self.assertEqual(0x1070809, f.total_size)
        self.assertEqual(0, f.chunk_id)

        # round trip
        fe = fountain_header(1, 0x1070809, 0)
        self.assertEqual(b'\x81\x07\x08\x09\x00\x00', bytes(fe))


class FountainTest(TestCase):
    def test_encode(self):
        data = b'0123456789' * 100
        inbuff = BytesIO(data)

        fes = fountain_encoder_stream(inbuff, 400, encode_id=0)
        r = fes.read(400)

        self.assertEqual(b'\x00\x00\x03\xe8\x00\x00' + data[:394], r)

    def test_round_trip(self):
        data = b'0123456789' * 100
        inbuff = BytesIO(data)
        fes = fountain_encoder_stream(inbuff, 400)

        outbuff = BytesIO()
        dec = fountain_decoder_stream(outbuff, 400)

        r = fes.read(400)
        self.assertFalse(dec.write(r))

        r = fes.read(400)
        self.assertFalse(dec.write(r))

        r = fes.read(400)
        self.assertTrue(dec.write(r))

        outbuff.seek(0)
        self.assertEqual(data, outbuff.read())
