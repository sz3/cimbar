#!/usr/bin/python3

"""fitness.py in out

evaluate which tiles are not being decoded properly
iterate over in by byte, by out over tile, e.g. <n> bits
use mismatches between decodes from out against encodes from in to determine what tiles are troublemakers

Usage:
  ./fitness.py <decoded_baseline> <encoded_image> [--dark] [--deskew=<0-3>]
  ./fitness.py (-h | --help)

Examples:
  python -m cimbar.fitness /tmp/baseline.py samples/4color1.jpg

Options:
  -h --help                        Show this help.
  --version                        Show version.
  --dark                           Use inverted palette.
  --deskew=<0-3>                   Deskew level. 0 is no deskew. Should be 0 or default, except for testing. [default: 3]
"""

from collections import defaultdict

from docopt import docopt

from cimbar.cimbar import decode_iter, encode_iter, get_deskew_params, BITS_PER_SYMBOL



class ErrorTracker:
    def __init__(self):
        self.errors = 0
        self.error_bits = 0
        self.total = 0

    def __iadd__(self, other):
        # other is an int, tuple, or errortracker
        if isinstance(other, int):
            self.total += other
        elif isinstance(other, tuple):
            self.errors += other[0]
            self.error_bits += other[1]
            self.total += other[2]
        else:
            self.errors += other.errors
            self.error_bits += other.error_bits
            self.total += other.total
        return self

    def __str__(self):
        return f'{self.errors}/{self.total}'

    def __repr__(self):
        return str(self)


def evaluate(src_file, dst_image, dark, deskew_params):
    # for byte in src_file, decoded_byte in dst_image:
    # if mismatch, tally tile information
    # also track bordering tiles? Edges may matter
    errors = 0
    errors_by_tile = defaultdict(ErrorTracker)

    ei = encode_iter(src_file, ecc=0)
    di = decode_iter(dst_image, dark, **deskew_params)
    for (expected_bits, x, y), actual_bits in zip(ei, di):
        if expected_bits != actual_bits:
            # print(f'!!! {expected_bits} != {actual_bits} at {x},{y}')
            err = bin(expected_bits ^ actual_bits).count('1')
            errors += err
            errors_by_tile[expected_bits] += (1, err, 1)
        else:
            errors_by_tile[expected_bits] += 1

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

    print('***')
    print(f'{errors} total bits incorrect')


def main():
    args = docopt(__doc__, version='cimbar fitness check 0.0.1')

    src_file = args['<decoded_baseline>']
    dst_image = args['<encoded_image>']
    dark = args.get('--dark')
    deskew_params = get_deskew_params(args.get('--deskew'))
    evaluate(src_file, dst_image, dark, deskew_params)


if __name__ == '__main__':
    main()
