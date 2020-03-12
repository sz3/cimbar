#!/usr/bin/python3

"""color-iconographic-matrix barcode

Usage:
  ./cimbar.py [<src_image> | --src_image=<filename>] [<dst_data> | --dst_data=<filename>]
  ./cimbar.py --encode [<src_data> | --src_data=<filename>] [<dst_image> | --dst_image=<filename>]
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
"""

import bitstring
import imagehash
from bitstring import Bits, BitStream
from docopt import docopt
from PIL import Image


CELL_SIZE = 8
CELL_SPACING = CELL_SIZE
CELL_DIMENSIONS = 128
MAX_ENCODING = 16384


class CimbTranslator:
    def __init__(self):
        self.hashes = {}
        for i in range(32):
            name = f'bitmap/{i:02x}.png'
            ahash = imagehash.average_hash(Image.open(name))
            self.hashes[i] = ahash

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


def decode(src_image, outfile):
    img = Image.open(src_image)
    ct = CimbTranslator()

    cols = CELL_DIMENSIONS
    cells = CELL_DIMENSIONS * cols

    with bit_file(outfile, bits_per_op=5, mode='write') as f:
        for i in range(cells):
            x = (i % cols) * CELL_SPACING
            y = (i // cols) * CELL_SPACING
            img_cell = img.crop((x, y, x + CELL_SIZE, y + CELL_SIZE))
            bits = ct.decode(img_cell)
            f.write(bits)


def main():
    args = docopt(__doc__, version='CIMBar 0.0.1')
    if args['--encode']:
        src_data = args['<src_data>'] or args['--src_data']
        dst_image = args['<dst_image>'] or args['--dst_image']
        return

    src_image = args['<src_image>'] or args['--src_image']
    dst_data = args['<dst_data>'] or args['--dst_data']
    decode(src_image, dst_data)


if __name__ == '__main__':
    main()