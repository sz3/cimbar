#!/usr/bin/python3

"""color-icon-matrix barcode
or symbol-matrix barcode?

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

from docopt import docopt
from PIL import Image

from cimbar.deskew.deskewer import deskewer
from cimbar.encode.cimb_translator import CimbTranslator, cell_drift, cell_positions
from cimbar.util.bit_file import bit_file


TOTAL_SIZE = 1024
BITS_PER_OP = 4
CELL_SIZE = 8
CELL_SPACING = CELL_SIZE + 1
CELL_DIMENSIONS = 112
CELLS_OFFSET = 8


def detect_and_deskew(src_image, temp_image, dark):
    deskewer(src_image, temp_image, dark)


def _decode_cell(ct, img, x, y, drift):
    best_distance = 1000
    for dx, dy in drift.pairs:
        testX = x + drift.x + dx
        testY = y + drift.y + dy
        img_cell = img.crop((testX, testY, testX + CELL_SIZE, testY + CELL_SIZE))
        bits, min_distance = ct.decode(img_cell)
        best_distance = min(min_distance, best_distance)
        if min_distance == best_distance:
            best_bits = bits  # + color bits?
            best_dx = dx
            best_dy = dy
        if min_distance < 8:
            break
    return best_bits, best_dx, best_dy


def decode_iter(src_image, dark, deskew):
    tempdir = None
    if deskew:
        tempdir = TemporaryDirectory()
        temp_img = path.join(tempdir.name, path.basename(src_image))
        detect_and_deskew(src_image, temp_img, dark)
        img = Image.open(temp_img)
    else:
        img = Image.open(src_image)
    ct = CimbTranslator(dark, bits=BITS_PER_OP)

    drift = cell_drift()
    for x, y in cell_positions(CELL_SPACING, CELL_DIMENSIONS, CELLS_OFFSET):
        best_bits, best_dx, best_dy = _decode_cell(ct, img, x, y, drift)
        drift.update(best_dx, best_dy)
        yield best_bits

    if tempdir:  # cleanup
        with tempdir:
            pass


def decode(src_image, outfile, dark=False, deskew=True):
    with bit_file(outfile, bits_per_op=BITS_PER_OP, mode='write') as f:
        for bits in decode_iter(src_image, dark, deskew):
            f.write(bits)


def _get_image_template(width, dark):
    color = (0, 0, 0) if dark else (255, 255, 255)
    img = Image.new('RGB', (width, width), color=color)

    suffix = 'dark' if dark else 'light'
    anchor = Image.open(f'bitmap/anchor-{suffix}.png')
    aw, ah = anchor.size
    img.paste(anchor, (0, 0))
    img.paste(anchor, (0, width-ah))
    img.paste(anchor, (width-aw, 0))
    img.paste(anchor, (width-aw, width-ah))

    horizontal_guide = Image.open(f'bitmap/guide-horizontal-{suffix}.png')
    gw, _ = horizontal_guide.size
    img.paste(horizontal_guide, (width//2 - gw//2, 3))
    img.paste(horizontal_guide, (width//2 - gw//2, width-5))

    vertical_guide = Image.open(f'bitmap/guide-vertical-{suffix}.png')
    _, gh = vertical_guide.size
    img.paste(vertical_guide, (3, width//2 - gw//2))
    img.paste(vertical_guide, (width-5, width//2 - gw//2))
    return img


def encode_iter(src_data):
    with bit_file(src_data, bits_per_op=BITS_PER_OP) as f:
        for x, y in cell_positions(CELL_SPACING, CELL_DIMENSIONS, CELLS_OFFSET):
            bits = f.read()
            yield bits, x, y


def encode(src_data, dst_image, dark=False):
    img = _get_image_template(TOTAL_SIZE, dark)
    ct = CimbTranslator(dark, bits=BITS_PER_OP)
    for bits, x, y in encode_iter(src_data):
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
