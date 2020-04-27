from os import path
from tempfile import TemporaryDirectory
from unittest import TestCase

from cimbar.cimbar import encode, decode


CIMBAR_ROOT = path.abspath(path.join(path.dirname(path.realpath(__file__)), '..'))


class CimbarTest(TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()

    def tearDown(self):
        with self.temp_dir:
            pass

    def test_round_trip(self):
        src_data = b'0123456789abcdefghij' * 1000
        src_path = path.join(self.temp_dir.name, 'infile.txt')
        with open(src_path, 'wb') as f:
            f.write(src_data)

        dst_image = path.join(self.temp_dir.name, 'encoded.png')
        encode(src_path, dst_image, dark=True)

        self.assertTrue(path.getsize(dst_image) > 0)

        out_path = path.join(self.temp_dir.name, 'outfile.txt')
        decode(dst_image, out_path, dark=True, deskew=False)

        with open(out_path, 'rb') as f:
            contents = f.read()

        self.assertEqual(len(contents), 8700)
        self.assertEqual(contents, src_data[:8700])
