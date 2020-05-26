#!/usr/bin/python3

"""grader.py clean.txt messy.txt

Using a clean output (encode -> decode, no camera distortion/blur/etc), we grade, bit-for-bit, the results of messy decode.

Usage:
  ./grader.py <decoded_baseline> <decoded_messy> [--dark]
  ./grader.py (-h | --help)

Examples:
  python -m cimbar.grader /tmp/baseline.py /tmp/messy.py

Options:
  -h --help                        Show this help.
  --version                        Show version.
  --dark                           Use inverted palette.
"""
from collections import defaultdict
from os.path import getsize

from docopt import docopt

from cimbar.cimbar import BITS_PER_OP
from cimbar.fitness import ErrorTracker, print_error_report
from cimbar.util.bit_file import bit_file


def evaluate(src_file, dst_file, bits_per_op, dark):
    error_bits = 0
    error_tiles = 0
    errors_by_tile = defaultdict(ErrorTracker)
    mismatch_by_tile = defaultdict(ErrorTracker)

    total_bits = getsize(src_file) * 8
    i = 0
    with bit_file(src_file, bits_per_op) as sf, bit_file(dst_file, bits_per_op) as df:
        while i < total_bits:
            expected_bits = sf.read()
            actual_bits = df.read()
            err = bin(expected_bits ^ actual_bits).count('1')
            error_bits += err
            if err:
                error_tiles += 1
                errors_by_tile[expected_bits] += (1, err, 1)
                mismatch_by_tile[actual_bits] += (1, err, 1)
            else:
                errors_by_tile[expected_bits] += 1
                mismatch_by_tile[actual_bits] += 1
            i += bits_per_op

    print_error_report(errors_by_tile)
    print('***')
    print('!!! mismatches:')
    print_error_report(mismatch_by_tile)

    print('***')
    print(f'total bits: {total_bits}')
    print(f'error bits: {error_bits}')
    print(f'error tiles: {error_tiles}')
    return error_bits


def main():
    args = docopt(__doc__, version='cimbar fitness check 0.0.1')

    src_file = args['<decoded_baseline>']
    dst_file = args['<decoded_messy>']
    dark = args.get('--dark')
    evaluate(src_file, dst_file, BITS_PER_OP, dark)


if __name__ == '__main__':
    main()
