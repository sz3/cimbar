'''
color-iconographic-matrix barcode
'''

import imagehash
import sys

from bitstring import Bits, BitStream
from PIL import Image


CELL_SIZE = 8


class Translator:
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


class OutputStream:
    def __init__(self, output_file):
        self.stream = BitStream()
        self.output_file = output_file

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.save()

    def write(self, bits):
        b1 = Bits(uint=bits, length=5)
        self.stream.append(b1)

    def save(self):
        with open(self.output_file, 'wb') as f:
            self.stream.tofile(f)
        print('wrote {}'.format(self.output_file))


def main():
    src_image = sys.argv[1]
    img = Image.open(src_image)
    tra = Translator()

    cols = 128
    cells = 128 * cols

    with OutputStream('/tmp/myfile.txt') as os:
        for i in range(cells):
            x = (i % cols) * CELL_SIZE
            y = (i // cols) * CELL_SIZE
            img_cell = img.crop((x, y, x + CELL_SIZE, y + CELL_SIZE))
            bits = tra.decode(img_cell)
            os.write(bits)


if __name__ == '__main__':
    main()