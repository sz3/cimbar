import random
from os import path
from tempfile import TemporaryDirectory
from unittest import TestCase

import cv2
import numpy

from cimbar.cimbar import encode, decode, bits_per_op
from cimbar.encode.rss import reed_solomon_stream
from cimbar.grader import evaluate as evaluate_grader


CIMBAR_ROOT = path.abspath(path.join(path.dirname(path.realpath(__file__)), '..'))


def _warp1(src_image, dst_image):
    img = cv2.imread(src_image)
    input_pts = [(0, 0), (0, 1023), (1023, 0), (1023, 1023)]
    output_pts = [(21, 212), (115, 943), (854, 198), (795, 942)]
    transformer = cv2.getPerspectiveTransform(numpy.float32(input_pts), numpy.float32(output_pts))
    img = cv2.warpPerspective(img, transformer, (1000, 1000))
    img = cv2.GaussianBlur(img,(3,3),0)
    cv2.imwrite(dst_image, img)


def _warp2(src_image, dst_image):
    img = cv2.imread(src_image)
    input_pts = [(1023, 1023), (1023, 0), (0, 1023), (0, 0)]
    output_pts = [(21, 212), (115, 943), (854, 198), (795, 942)]
    transformer = cv2.getPerspectiveTransform(numpy.float32(input_pts), numpy.float32(output_pts))
    img = cv2.warpPerspective(img, transformer, (1000, 1000))
    img = cv2.GaussianBlur(img,(3,3),0)
    cv2.imwrite(dst_image, img)


class CimbarTest(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs_dir = TemporaryDirectory()

        cls.src_file = path.join(cls.inputs_dir.name, 'infile.txt')
        random_data = bytearray(random.getrandbits(8) for _ in range(4000))
        src_data = random_data * 4
        with open(cls.src_file, 'wb') as f:
            f.write(src_data)

        cls.encoded_file = path.join(cls.inputs_dir.name, 'encoded.png')
        encode(cls.src_file, cls.encoded_file, dark=True)

        cls.decode_clean = path.join(cls.inputs_dir.name, 'decode-no-ecc-clean.txt')
        with reed_solomon_stream(cls.src_file, 30, 155) as rss, open(cls.decode_clean, 'wb') as f:
            f.write(rss.read(7500))

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
        self.assertEqual(len(contents), 7500)
        self.assertEqual(contents, self._src_data()[:7500])

    def validate_grader(self, out_path, target):
        num_bits = evaluate_grader(self.decode_clean, out_path, bits_per_op(), True)
        self.assertLess(num_bits, target)

    def test_decode_simple(self):
        self.assertTrue(path.getsize(self.encoded_file) > 0)

        out_path = self._temp_path('outfile.txt')
        decode([self.encoded_file], out_path, dark=True, deskew=False)
        self.validate_output(out_path)

        out_no_ecc = self._temp_path('outfile_no_ecc.txt')
        decode([self.encoded_file], out_no_ecc, dark=True, ecc=0, deskew=False)
        self.validate_grader(out_no_ecc, 1)

        out_no_ecc = self._temp_path('outfile_no_ecc.txt')
        decode([self.encoded_file], out_no_ecc, dark=True, ecc=0)
        self.validate_grader(out_no_ecc, 200)

    def test_decode_perspective(self):
        skewed_image = self._temp_path('skewed.jpg')
        _warp1(self.encoded_file, skewed_image)

        out_no_ecc = self._temp_path('outfile_no_ecc.txt')
        decode([skewed_image], out_no_ecc, dark=True, ecc=0, force_preprocess=True)
        self.validate_grader(out_no_ecc, 2000)

    def test_decode_perspective_rotate(self):
        skewed_image = self._temp_path('skewed2.jpg')
        _warp2(self.encoded_file, skewed_image)

        out_no_ecc = self._temp_path('outfile_no_ecc2.txt')
        decode([skewed_image], out_no_ecc, dark=True, ecc=0, force_preprocess=True)
        self.validate_grader(out_no_ecc, 4000)

    def test_decode_sample(self):
        clean_image = 'samples/6bit/4color_ecc30_0.png'
        warped_image = 'samples/6bit/4_30_802.jpg'

        clean_bits = self._temp_path('outfile_clean.txt')
        decode([clean_image], clean_bits, dark=True, ecc=0, auto_dewarp=False)

        warped_bits = self._temp_path('outfile_warped.txt')
        decode([warped_image], warped_bits, dark=True, ecc=0, force_preprocess=True, auto_dewarp=False)

        num_bits = evaluate_grader(clean_bits, warped_bits, bits_per_op(), True)
        self.assertLess(num_bits, 350)


class RoundtripTest(TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()

        self.src_file = path.join(self.temp_dir.name, 'infile.txt')
        random_data = bytearray(random.getrandbits(8) for _ in range(4000))
        src_data = random_data * 4
        with open(self.src_file, 'wb') as f:
            f.write(src_data)

    def tearDown(self):
        with self.temp_dir:
            pass

    def test_roundtrip(self):
        dst_image = path.join(self.temp_dir.name, 'encode.png')
        encode(self.src_file, dst_image, dark=True, fountain=True)

        out_path = path.join(self.temp_dir.name, 'out.txt')
        decode([dst_image], out_path, dark=True, deskew=False, auto_dewarp=False, fountain=True)

        with open(out_path, 'rb') as f:
            contents = f.read()
        with open(self.src_file, 'rb') as f:
            expected = f.read()
        self.assertEquals(contents, expected)
