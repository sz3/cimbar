from os import path
from tempfile import TemporaryDirectory
from unittest import TestCase

from cimbar.cimbar import encode, decode, BITS_PER_OP
from cimbar.grader import evaluate as evaluate_grader


CIMBAR_ROOT = path.abspath(path.join(path.dirname(path.realpath(__file__)), '..'))


class CimbarTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs_dir = TemporaryDirectory()

        cls.src_file = path.join(cls.inputs_dir.name, 'infile.txt')
        src_data = b'0123456789abcdefghij' * 1000
        with open(cls.src_file, 'wb') as f:
            f.write(src_data)

        cls.decode_clean = path.join(cls.inputs_dir.name, 'infile-trunc-clean.txt')
        with open(cls.decode_clean, 'wb') as f:
            f.write(src_data[:9300])

        cls.encoded_file = path.join(cls.inputs_dir.name, 'encoded.png')
        encode(cls.src_file, cls.encoded_file, dark=True)

        cls.encoded_no_ecc = path.join(cls.inputs_dir.name, 'encoded_no_ecc.png')
        encode(cls.src_file, cls.encoded_no_ecc, dark=True, ecc=0)

    @classmethod
    def tearDownClass(cls):
        with cls.inputs_dir:
            pass

    def setUp(self):
        self.temp_dir = TemporaryDirectory()

    def tearDown(self):
        with self.temp_dir:
            pass

    def _temp_path(self, filename):
        return path.join(self.temp_dir.name, filename)

    def _src_data(self):
        with open(self.src_file, 'rb') as f:
            return f.read()

    def validate_output(self, out_path):
        with open(out_path, 'rb') as f:
            contents = f.read()
        self.assertEqual(len(contents), 8400)
        self.assertEqual(contents, self._src_data()[:8400])

    def validate_grader(self, out_path, target):
        num_bits = evaluate_grader(self.decode_clean, out_path, BITS_PER_OP, True)
        self.assertLess(num_bits, target)

    def test_decode_simple(self):
        self.assertTrue(path.getsize(self.encoded_file) > 0)

        out_path = self._temp_path('outfile.txt')
        decode(self.encoded_file, out_path, dark=True, deskew=False)
        self.validate_output(out_path)

        out_no_ecc = self._temp_path('outfile_no_ecc.txt')
        decode(self.encoded_no_ecc, out_no_ecc, dark=True, ecc=0, deskew=False)
        self.validate_grader(out_no_ecc, 1)

        out_no_ecc = self._temp_path('outfile_no_ecc.txt')
        decode(self.encoded_no_ecc, out_no_ecc, dark=True, ecc=0)
        self.validate_grader(out_no_ecc, 200)
