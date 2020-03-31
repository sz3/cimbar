import sys

from cimbar.cimbar import decode_iter, encode_iter

# fitness.py in out

# evaluate which tiles are not being decoded properly
# iterate over in by byte, by out over tile, e.g. <n> bits
# use mismatches between decodes from out against encodes from in to determine what tiles are troublemakers

def evaluate(src_file, dst_image, dark, deskew):
    # for byte in src_file, decoded_byte in dst_image:
    # if mismatch, tally tile information
    # also track bordering tiles? Edges may matter
    results = {}

    ei = encode_iter(src_file)
    di = decode_iter(dst_image, dark, deskew, partial_deskew=True)
    for (expected_bits, x, y), actual_bits in zip(ei, di):
        r = results.get(expected_bits, [0,0])
        r[1] += 1
        if expected_bits != actual_bits:
            print(f'!!! {expected_bits} != {actual_bits} at {x},{y}')
            r[0] += 1
        results[expected_bits] = r

    print('final result:')
    s = {f'{k:02x}': v for k, v in sorted(results.items(), key=lambda item: item[1][0] / item[1][1])}
    print(s)


def main():
    src_file = sys.argv[1]
    dst_image = sys.argv[2]
    evaluate(src_file, dst_image, dark=True, deskew=True)


if __name__ == '__main__':
    main()
