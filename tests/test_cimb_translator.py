from os import path
from unittest import TestCase

from PIL import Image

from cimbar.encode.cimb_translator import CimbDecoder


CIMBAR_ROOT = path.abspath(path.join(path.dirname(path.realpath(__file__)), '..'))


class CimbDecoderTest(TestCase):
    '''def test_decode_symbol_monochome(self):
        cimb = CimbDecoder(False, 4)
        for i in range(10):
            img_path = path.join(CIMBAR_ROOT, 'bitmap', '4', f'{i:02x}.png')
            print(img_path)
            img = Image.open(img_path)
            decoded, error = cimb.decode_symbol(img)
            self.assertEqual(decoded, i)
            self.assertEqual(error, 0)
            img.close()'''

    def test_decode_symbol_dark(self):
        cimb = CimbDecoder(True, 4)
        img_path = path.join(CIMBAR_ROOT, 'tests', 'sample', '05.png')
        img = Image.open(img_path)
        decoded, error = cimb.decode_symbol(img)
        self.assertEqual(decoded, 5)
        self.assertEqual(error, 0)
