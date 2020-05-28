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

from collections import defaultdict

from docopt import docopt

from cimbar.cimbar import decode_iter, encode_iter, get_deskew_params, BITS_PER_SYMBOL
from cimbar.grader import Grader


def print_error_report(errors_by_tile):
    num_symbols = 2 ** BITS_PER_SYMBOL
    errors_by_symbol = defaultdict(ErrorTracker)
    errors_by_color = defaultdict(ErrorTracker)
    for tile, et in errors_by_tile.items():
        color = tile // num_symbols
        symbol = tile % num_symbols
        errors_by_color[color] += et
        errors_by_symbol[symbol] += et

    print('***')
    print('final result by symbol:')
    s = {f'{k:02x}': v for k, v in sorted(errors_by_symbol.items(), key=lambda item: item[1].errors / item[1].total)}
    print(s)

    print('final result by color:')
    c = {f'{k:02x}': v for k, v in sorted(errors_by_color.items(), key=lambda item: item[1].errors / item[1].total)}
    print(c)


def print_mismatch_matrix(mismatch_matrix):
    num_symbols = 2 ** BITS_PER_SYMBOL
    mismatch_by_symbol = defaultdict(lambda: defaultdict(int))
    mismatch_by_color = defaultdict(lambda: defaultdict(int))
    for tile, mat in mismatch_matrix.items():
        at = tile % num_symbols
        ac = tile // num_symbols
        for expected, count in mat.items():
            et = expected % num_symbols
            ec = expected // num_symbols
            if ac != ec:
                mismatch_by_color[ac][ec] += 1
            if at != et:
                mismatch_by_symbol[at][et] += 1
    print('****')
    print('mismatch breakdown')
    print('****')
    print(mismatch_by_symbol)
    print(mismatch_by_color)


def evaluate(src_file, dst_image, dark, force_preprocess, deskew_params):
    # for byte in src_file, decoded_byte in dst_image:
    # if mismatch, tally tile information
    # also track bordering tiles? Edges may matter
    g = Grader()
    mismatch_matrix = defaultdict(lambda: defaultdict(int))

    ei = encode_iter(src_file, ecc=0)
    di = decode_iter(dst_image, dark, force_preprocess, **deskew_params)
    for (expected_bits, x, y), actual_bits in zip(ei, di):
        g.grade(expected_bits, actual_bits)
        if expected_bits != actual_bits:
            mismatch_matrix[actual_bits][expected_bits] += 1

    g.print_report()
    print_mismatch_matrix(mismatch_matrix)
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
