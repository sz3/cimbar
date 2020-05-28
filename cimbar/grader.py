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

from cimbar.cimbar import BITS_PER_OP, BITS_PER_SYMBOL
from cimbar.util.bit_file import bit_file


class ErrorTracker:
    def __init__(self):
        self.errors = 0
        self.error_bits = 0
        self.total = 0

    def __iadd__(self, other):
        # other is an int, tuple, or errortracker
        if isinstance(other, int):
            self.total +=1
            if other > 0:
                self.errors += 1
                self.error_bits += other
        else:
            self.errors += other.errors
            self.error_bits += other.error_bits
            self.total += other.total
        return self

    def __str__(self):
        return f'{self.errors}/{self.total}'

    def __repr__(self):
        return str(self)


def _split_bits(expected_bits, actual_bits):
    mask = ((2**BITS_PER_SYMBOL)-1)
    expected_symbols = expected_bits & mask
    expected_color = expected_bits >> BITS_PER_SYMBOL
    actual_symbols = actual_bits & mask
    actual_color = actual_bits >> BITS_PER_SYMBOL

    symbol_err = bin(expected_symbols ^ actual_symbols).count('1')
    color_err = bin(expected_color ^ actual_color).count('1')
    return expected_symbols, expected_color, actual_symbols, actual_color, symbol_err, color_err


def _print_sorted(etdict):
    s = {f'{k:02x}': v for k, v in sorted(etdict.items(), key=lambda item: item[1].errors / item[1].total)}
    print(s)


def evaluate(src_file, dst_file, bits_per_op, dark):
    error_bits = 0
    symbol_error_bits = 0
    color_error_bits = 0
    error_tiles = 0
    errors_by_symbol = defaultdict(ErrorTracker)
    errors_by_color = defaultdict(ErrorTracker)
    mismatch_by_symbol = defaultdict(ErrorTracker)
    mismatch_by_color = defaultdict(ErrorTracker)

    total_bits = getsize(src_file) * 8
    i = 0
    with bit_file(src_file, bits_per_op) as sf, bit_file(dst_file, bits_per_op) as df:
        while i < total_bits:
            expected_bits = sf.read()
            actual_bits = df.read()
            err = bin(expected_bits ^ actual_bits).count('1')
            if err:
                error_bits += err
                error_tiles += 1

            expected_symbols, expected_color, actual_symbols, actual_color, symbol_err, color_err = (
                    _split_bits(expected_bits, actual_bits)
            )

            symbol_error_bits += symbol_err
            color_error_bits += color_err

            errors_by_symbol[expected_symbols] += symbol_err
            errors_by_color[expected_color] += color_err
            mismatch_by_symbol[actual_symbols] += symbol_err
            mismatch_by_color[actual_color] += color_err

            i += bits_per_op

    _print_sorted(errors_by_symbol)
    _print_sorted(errors_by_color)
    print('***')
    print('!!! mismatches:')
    _print_sorted(mismatch_by_symbol)
    _print_sorted(mismatch_by_color)

    print('***')
    print(f'total bits: {total_bits}')
    print(f'error bits: {error_bits}')
    print(f'symbol error bits: {symbol_error_bits}')
    print(f'color error bits: {color_error_bits}')
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
