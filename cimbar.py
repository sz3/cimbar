#!/usr/bin/python3

"""color-iconographic-matrix barcode

Usage:
  ./cimbar.py (<src_image> | --src_image=<filename>) (<dst_data> | --dst_data=<filename>) [--deskew] [--dark]
  ./cimbar.py --encode (<src_data> | --src_data=<filename>) (<dst_image> | --dst_image=<filename>) [--dark]
  ./cimbar.py (-h | --help)

Examples:
  python -m cimbar --encode myfile.txt cimb-code.png
  python -m cimbar cimb-code.png myfile.txt

Options:
  -h --help                        Show this help.
  --version                        Show version.
  --dst_data=<filename>            For decoding. Where to store decoded data.
  --dst_image=<filename>           For encoding. Where to store encoded image.
  --src_data=<filename>            For encoding. Data to encode.
  --src_image=<filename>           For decoding. Image to try to decode
  --dark                           Use dark mode.
"""
from os import path
from tempfile import TemporaryDirectory

import bitstring
import imagehash
from bitstring import Bits, BitStream
from docopt import docopt
from PIL import Image


BITS_PER_OP = 5
CELL_SIZE = 8
CELL_SPACING = CELL_SIZE + 1
CELL_DIMENSIONS = 113
MAX_ENCODING = 16384


class CimbTranslator:
    def __init__(self, dark):
        self.dark = dark
        self.hashes = {}
        self.img = {}
        for i in range(32):
            name = f'bitmap/{i:02x}.png'
            self.img[i] = self._load_img(name)
            ahash = imagehash.average_hash(self.img[i])
            self.hashes[i] = ahash

    def _load_img(self, name):
        img = Image.open(name)
        if not self.dark:
            return img

        pixdata = img.load()
        width, height = img.size
        for y in range(height):
            for x in range(width):
                if pixdata[x, y] == (255, 255, 255, 255):
                    pixdata[x, y] = (0, 0, 0, 255)
        return img

    def get_best_fit(self, cell_hash):
        min_distance = 1000
        best_fit = 0
        for i, ihash in self.hashes.items():
            distance = cell_hash - ihash
            if distance < min_distance:
                min_distance = distance
                best_fit = i
            if min_distance == 0:
                break
        if min_distance > 0:
            print(f'min distance is {min_distance}. best fit {best_fit}')
        return best_fit

    def decode(self, img_cell):
        cell_hash = imagehash.average_hash(img_cell)
        return self.get_best_fit(cell_hash)

    def encode(self, bits):
        return self.img[bits]


class bit_file:
    def __init__(self, filename, bits_per_op, mode='read'):
        if mode not in ['read', 'write']:
            raise Exception('bad bit_file mode. Try "read" or "write"')
        self.mode = 'wb' if mode == 'write' else 'rb'

        self.f = open(filename, self.mode)
        self.bits_per_op = bits_per_op
        self.stream = BitStream()
        if mode == 'read':
            self.stream.append(Bits(bytes=self.f.read(MAX_ENCODING)))

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self.mode == 'wb':
            self.save()
        with self.f:  # close file
            pass

    def write(self, bits):
        b1 = Bits(uint=bits, length=self.bits_per_op)
        self.stream.append(b1)

    def read(self):
        try:
            bits = self.stream.read(f'uint:{self.bits_per_op}')
        except bitstring.ReadError:
            try:
                bits = self.stream.read('uint')
            except bitstring.InterpretError:
                bits = 0
        return bits

    def save(self):
        self.stream.tofile(self.f)


def cell_positions(spacing, dimensions, marker_size=8):
    '''
    8 tiles at top is 128-16 == 112
    8 tiles at bottom is also 128-16 == 112

    112 * 8
    128 * 112
    112 * 8
    '''
    #cells = dimensions * dimensions
    marker_offset_x = spacing * marker_size
    top_width = dimensions - marker_size - marker_size
    top_cells = top_width * marker_size
    for i in range(top_cells):
        x = (i % top_width) * spacing + marker_offset_x
        y = (i // top_width) * spacing
        yield x, y

    mid_y = marker_size * spacing
    mid_width = dimensions
    mid_cells = mid_width * top_width  # top_width is also "mid_height"
    for i in range(mid_cells):
        x = (i % mid_width) * spacing
        y = (i // mid_width) * spacing + mid_y
        yield x, y

    bottom_y = (dimensions - marker_size) * spacing
    bottom_width = top_width
    bottom_cells = bottom_width * marker_size
    for i in range(bottom_cells):
        x = (i % bottom_width) * spacing + marker_offset_x
        y = (i // bottom_width) * spacing + bottom_y
        yield x, y


def detect_and_deskew(src_image, temp_image, dark):
    from scanner import deskewer
    deskewer(src_image, temp_image, dark)


def decode(src_image, outfile, dark=False, deskew=True):
    tempdir = None
    if deskew:
        tempdir = TemporaryDirectory()
        temp_img = path.join(tempdir.name, path.basename(src_image))
        detect_and_deskew(src_image, temp_img, dark)
        img = Image.open(temp_img)
    else:
        img = Image.open(src_image)
    ct = CimbTranslator(dark)

    with bit_file(outfile, bits_per_op=BITS_PER_OP, mode='write') as f:
        for x, y in cell_positions(CELL_SPACING, CELL_DIMENSIONS):
            img_cell = img.crop((x, y, x + CELL_SIZE, y + CELL_SIZE))
            bits = ct.decode(img_cell)
            f.write(bits)

    if tempdir:  # cleanup
        with tempdir:
            pass


def encode(src_data, dst_image, dark=False):
    img = Image.open('bitmap/template.png')
    ct = CimbTranslator(dark)

    with bit_file(src_data, bits_per_op=BITS_PER_OP) as f:
        for x, y in cell_positions(CELL_SPACING, CELL_DIMENSIONS):
            bits = f.read()
            encoded = ct.encode(bits)
            img.paste(encoded, (x, y))
    img.save(dst_image)


def main():
    args = docopt(__doc__, version='CIMBar 0.0.1')

    dark = args['--dark']
    if args['--encode']:
        src_data = args['<src_data>'] or args['--src_data']
        dst_image = args['<dst_image>'] or args['--dst_image']
        encode(src_data, dst_image, dark)
        return

    src_image = args['<src_image>'] or args['--src_image']
    dst_data = args['<dst_data>'] or args['--dst_data']
    decode(src_image, dst_data, dark, args['--deskew'])


if __name__ == '__main__':
    main()