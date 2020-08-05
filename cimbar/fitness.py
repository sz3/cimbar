#!/usr/bin/python3

"""fitness.py in out

evaluate which tiles are not being decoded properly
iterate over in by byte, by out over tile, e.g. <n> bits
use mismatches between decodes from out against encodes from in to determine what tiles are troublemakers

Usage:
  ./fitness.py <decoded_baseline> <encoded_image> [--dark] [--deskew=<0-2>] [--force-preprocess]
  ./fitness.py (-h | --help)

Examples:
  python -m cimbar.fitness /tmp/baseline.py samples/4color1.jpg

Options:
  -h --help                        Show this help.
  --version                        Show version.
  --dark                           Use inverted palette.
  --deskew=<0-2>                   Deskew level. 0 is no deskew. Should be 0 or default, except for testing. [default: 2]
  --force-preprocess               Always run sharpening filters on image before decoding.
"""

from docopt import docopt

from cimbar.cimbar import decode_iter, encode_iter, get_deskew_params, CELL_SPACING, CELL_DIMENSIONS, CELLS_OFFSET
from cimbar.encode.cell_positions import cell_positions
from cimbar.grader import Grader


def evaluate(src_file, dst_image, dark, force_preprocess, deskew_params):
    # for byte in src_file, decoded_byte in dst_image:
    # if mismatch, tally tile information
    # also track bordering tiles? Edges may matter
    g = Grader()

    expected = {(x, y): bits for bits, x, y in encode_iter(src_file, ecc=0)}
    pos = cell_positions(CELL_SPACING, CELL_DIMENSIONS, CELLS_OFFSET)

    di = decode_iter(dst_image, dark, force_preprocess, **deskew_params)
    for i, actual_bits in di:
        expected_bits = expected[pos[i]]
        g.grade(expected_bits, actual_bits)

    g.print_report()
    return g.error_bits


def main():
    args = docopt(__doc__, version='cimbar fitness check 0.0.1')

    src_file = args['<decoded_baseline>']
    dst_image = args['<encoded_image>']
    dark = args.get('--dark')
    deskew_params = get_deskew_params(args.get('--deskew'))
    force_preprocess = args.get('--force-preprocess')
    evaluate(src_file, dst_image, dark, force_preprocess, deskew_params)


if __name__ == '__main__':
    main()
