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

from docopt import docopt
from PIL import Image

from cimbar.deskew.deskewer import deskewer
from cimbar.encode.cimb_translator import CimbTranslator, cell_drift, cell_positions
from cimbar.encode.rss import reed_solomon_stream
from cimbar.util.bit_file import bit_file


BITS_PER_OP = 5
CELL_SIZE = 8
CELL_SPACING = CELL_SIZE + 1
CELL_DIMENSIONS = 113


def detect_and_deskew(src_image, temp_image, dark):
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

    drift = cell_drift()
    with reed_solomon_stream(outfile, mode='write') as rss, bit_file(rss, bits_per_op=BITS_PER_OP, mode='write') as f:
        for x, y in cell_positions(CELL_SPACING, CELL_DIMENSIONS):
            best_distance = 1000
            for dx, dy in drift.pairs:
                testX = x + drift.x + dx
                testY = y + drift.y + dy
                img_cell = img.crop((testX, testY, testX + CELL_SIZE, testY + CELL_SIZE))
                bits, min_distance = ct.decode(img_cell)
                best_distance = min(min_distance, best_distance)
                if min_distance == best_distance:
                    best_bits = bits
                    best_dx = dx
                    best_dy = dy
                if min_distance < 8:
                    break
            f.write(best_bits)
            drift.update(best_dx, best_dy)

    if tempdir:  # cleanup
        with tempdir:
            pass


def _get_image_template(width, dark):
    color = (0, 0, 0) if dark else (255, 255, 255)
    img = Image.new('RGB', (width, width), color=color)
    anchor_src = 'bitmap/anchor-dark.png' if dark else 'bitmap/anchor-light.png'
    anchor = Image.open(anchor_src)
    aw, ah = anchor.size
    img.paste(anchor, (0, 0))
    img.paste(anchor, (0, width-ah))
    img.paste(anchor, (width-aw, 0))
    img.paste(anchor, (width-aw, width-ah))
    return img


def encode(src_data, dst_image, dark=False):
    img = _get_image_template(1024, dark)
    ct = CimbTranslator(dark)

    with reed_solomon_stream(src_data) as rss, bit_file(rss, bits_per_op=BITS_PER_OP) as f:
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
