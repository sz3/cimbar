#!/usr/bin/python3

"""color-icon-matrix barcode

Usage:
  ./cimbar.py <IMAGES>... --output=<filename> [--dark | --light] [--colorbits=<0-3>] [--deskew=<0-2>] [--ecc=<0-150>]
                         [--fountain] [--preprocess=<0,1>] [--color-correct=<0-2>]
  ./cimbar.py --encode (<src_data> | --src_data=<filename>) (<output> | --output=<filename>) [--dark | --light]
                       [--colorbits=<0-3>] [--ecc=<0-150>] [--fountain]
  ./cimbar.py (-h | --help)

Examples:
  python -m cimbar --encode myfile.txt cimb-code.png
  python -m cimbar cimb-code.png -o myfile.txt

Options:
  -h --help                        Show this help.
  --version                        Show version.
  --src_data=<filename>            For encoding. Data to encode.
  -o --output=<filename>           For encoding. Where to store output. For encodes, this may be interpreted as a prefix.
  -c --colorbits=<0-3>             How many colorbits in the image. [default: 2]
  -e --ecc=<0-150>                 Reed solomon error correction level. 0 is no ecc. [default: 30]
  -f --fountain                    Use fountain encoding scheme.
  --dark                           Use dark palette. [default]
  --light                          Use light palette.
  --color-correct=<0-2>            Color correction. 0 is off. 1 is white balance. 2 is 2-pass least squares. [default: 1]
  --deskew=<0-2>                   Deskew level. 0 is no deskew. Should usually be 0 or default. [default: 1]
  --preprocess=<0,1>               Sharpen image before decoding. Default is to guess. [default: -1]
"""
from os import path
from tempfile import TemporaryDirectory

import cv2
import numpy
from docopt import docopt
from PIL import Image

from cimbar.deskew.deskewer import deskewer
from cimbar.encode.cell_positions import cell_positions, AdjacentCellFinder, FloodDecodeOrder
from cimbar.encode.cimb_translator import CimbEncoder, CimbDecoder, avg_color, possible_colors
from cimbar.encode.rss import reed_solomon_stream
from cimbar.util.bit_file import bit_file
from cimbar.util.interleave import interleave, interleave_reverse, interleaved_writer


TOTAL_SIZE = 1024
BITS_PER_SYMBOL = 4
BITS_PER_COLOR = 2
CELL_SIZE = 8
CELL_SPACING = CELL_SIZE + 1
CELL_DIMENSIONS = 112
CELLS_OFFSET = 8
ECC = 30
INTERLEAVE_BLOCKS = 155
INTERLEAVE_PARTITIONS = 2
FOUNTAIN_BLOCKS = 10


def get_deskew_params(level):
    level = int(level)
    return {
        'deskew': level,
        'auto_dewarp': level >= 2,
    }


def bits_per_op():
    return BITS_PER_SYMBOL + BITS_PER_COLOR


def _fountain_chunk_size(ecc=ECC, bits_per_op=bits_per_op(), fountain_blocks=FOUNTAIN_BLOCKS):
    return int((155-ecc) * bits_per_op * 10 / fountain_blocks)


def detect_and_deskew(src_image, temp_image, dark, auto_dewarp=True):
    return deskewer(src_image, temp_image, dark, auto_dewarp=auto_dewarp)


def _decode_cell(ct, img, color_img, x, y, drift):
    best_distance = 1000
    for dx, dy in drift.pairs:
        testX = x + drift.x + dx
        testY = y + drift.y + dy
        img_cell = img.crop((testX, testY, testX + CELL_SIZE, testY + CELL_SIZE))
        bits, min_distance = ct.decode_symbol(img_cell)
        best_distance = min(min_distance, best_distance)
        if min_distance == best_distance:
            best_bits = bits
            best_dx = dx
            best_dy = dy
        if min_distance < 8:
            break

    testX = x + drift.x + best_dx
    testY = y + drift.y + best_dy
    best_cell = color_img.crop((testX+1, testY+1, testX + CELL_SIZE-2, testY + CELL_SIZE-2))
    return best_bits + ct.decode_color(best_cell), best_dx, best_dy, best_distance


def _preprocess_for_decode(img):
    ''' This might need to be conditional based on source image size.'''
    img = cv2.cvtColor(numpy.array(img), cv2.COLOR_RGB2BGR)
    kernel = numpy.array([[-1.0,-1.0,-1.0], [-1.0,8.5,-1.0], [-1.0,-1.0,-1.0]])
    img = cv2.filter2D(img, -1, kernel)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = Image.fromarray(img)
    return img


def _get_decoder_stream(outfile, ecc, fountain):
    # set up the outstream: image -> reedsolomon -> fountain -> zstd_decompress -> raw bytes
    f = open(outfile, 'wb')
    if fountain:
        import zstandard as zstd
        from cimbar.fountain.fountain_decoder_stream import fountain_decoder_stream
        decompressor = zstd.ZstdDecompressor().stream_writer(f)
        f = fountain_decoder_stream(decompressor, _fountain_chunk_size(ecc))
    on_rss_failure = b'' if fountain else None
    return reed_solomon_stream(f, ecc, mode='write', on_failure=on_rss_failure) if ecc else f


def compute_tint(img, dark):
    def update(c, r, g, b):
        c['r'] = max(c['r'], r)
        c['g'] = max(c['g'], g)
        c['b'] = max(c['b'], b)

    cc = {}
    cc['r'] = cc['g'] = cc['b'] = 1

    if dark:
        pos = [(28, 28), (28, 992), (992, 28)]
    else:
        pos = [(67, 0), (0, 67), (945, 0), (0, 945)]

    for x, y in pos:
        iblock = img.crop((x, y, x + 4, y + 4))
        r, g, b = avg_color(iblock)
        update(cc, *avg_color(iblock))

    print(f'tint is {cc}')
    return cc['r'], cc['g'], cc['b']


def _decode_iter(ct, img, color_img):
    cell_pos = cell_positions(CELL_SPACING, CELL_DIMENSIONS, CELLS_OFFSET)
    finder = AdjacentCellFinder(cell_pos, CELL_DIMENSIONS)
    decode_order = FloodDecodeOrder(cell_pos, finder)
    for i, (x, y), drift in decode_order:
        best_bits, best_dx, best_dy, best_distance = _decode_cell(ct, img, color_img, x, y, drift)
        decode_order.update(best_dx, best_dy, best_distance)
        yield i, best_bits


def decode_iter(src_image, dark, should_preprocess, color_correct, deskew, auto_dewarp):
    tempdir = None
    if deskew:
        tempdir = TemporaryDirectory()
        temp_img = path.join(tempdir.name, path.basename(src_image))
        dims = detect_and_deskew(src_image, temp_img, dark, auto_dewarp)
        if should_preprocess < 0:
            should_preprocess = dims[0] < TOTAL_SIZE or dims[1] < TOTAL_SIZE
        color_img = Image.open(temp_img)
    else:
        color_img = Image.open(src_image)

    ct = CimbDecoder(dark, symbol_bits=BITS_PER_SYMBOL, color_bits=BITS_PER_COLOR)
    img = _preprocess_for_decode(color_img) if should_preprocess else color_img

    if color_correct:
        from colormath.chromatic_adaptation import _get_adaptation_matrix
        ct.ccm = white = _get_adaptation_matrix(numpy.array([*compute_tint(color_img, dark)]),
                                        numpy.array([255, 255, 255]), 2, 'von_kries')
        if color_correct == 2:
            for i in _decode_iter(ct, img, color_img):
                pass
            print(ct.color_metrics)

            observed = [c for _, c in ct.color_metrics]
            exp = numpy.array(possible_colors(dark, BITS_PER_COLOR))
            from colour.characterisation.correction import matrix_colour_correction_Cheung2004
            der = matrix_colour_correction_Cheung2004(observed, exp)
            ct.ccm = der.dot(white)

    yield from _decode_iter(ct, img, color_img)

    if tempdir:  # cleanup
        with tempdir:
            pass

    print('decoder avg colors:')
    print(ct.color_metrics)


def decode(src_images, outfile, dark=False, ecc=ECC, fountain=False, force_preprocess=False, color_correct=False,
           deskew=True, auto_dewarp=True):
    cells = cell_positions(CELL_SPACING, CELL_DIMENSIONS, CELLS_OFFSET)
    interleave_lookup, block_size = interleave_reverse(cells, INTERLEAVE_BLOCKS, INTERLEAVE_PARTITIONS)
    dstream = _get_decoder_stream(outfile, ecc, fountain)
    with dstream as outstream:
        for imgf in src_images:
            with interleaved_writer(f=outstream, bits_per_op=bits_per_op(), mode='write', keep_open=True) as iw:
                decoding = {i: bits for i, bits in decode_iter(imgf, dark, force_preprocess, color_correct, deskew,
                                                               auto_dewarp)}
                for i, bits in sorted(decoding.items()):
                    block = interleave_lookup[i] // block_size
                    iw.write(bits, block)


def _get_image_template(width, dark):
    color = (0, 0, 0) if dark else (255, 255, 255)
    img = Image.new('RGB', (width, width), color=color)

    suffix = 'dark' if dark else 'light'
    anchor = Image.open(f'bitmap/anchor-{suffix}.png')
    anchor_br = Image.open(f'bitmap/anchor-secondary-{suffix}.png')
    aw, ah = anchor.size
    img.paste(anchor, (0, 0))
    img.paste(anchor, (0, width-ah))
    img.paste(anchor, (width-aw, 0))
    img.paste(anchor_br, (width-aw, width-ah))

    horizontal_guide = Image.open(f'bitmap/guide-horizontal-{suffix}.png')
    gw, _ = horizontal_guide.size
    img.paste(horizontal_guide, (width//2 - gw//2, 2))
    img.paste(horizontal_guide, (width//2 - gw//2, width-4))
    img.paste(horizontal_guide, (width//2 - gw - gw//2, width-4))  # long bottom guide
    img.paste(horizontal_guide, (width//2 + gw - gw//2, width-4))  # ''

    vertical_guide = Image.open(f'bitmap/guide-vertical-{suffix}.png')
    _, gh = vertical_guide.size
    img.paste(vertical_guide, (2, width//2 - gw//2))
    img.paste(vertical_guide, (width-4, width//2 - gw//2))
    return img


def _get_encoder_stream(src, ecc, fountain, compression_level=6):
    # various checks to set up the instream.
    # the hierarchy is raw bytes -> zstd -> fountain -> reedsolomon -> image
    f = open(src, 'rb')
    if fountain:
        import zstandard as zstd
        from cimbar.fountain.fountain_encoder_stream import fountain_encoder_stream
        reader = zstd.ZstdCompressor(level=compression_level).stream_reader(f)
        f = fountain_encoder_stream(reader, _fountain_chunk_size(ecc))
    estream = reed_solomon_stream(f, ecc) if ecc else f

    read_size = _fountain_chunk_size(ecc) if fountain else 16384
    read_count = (f.len // read_size) * 2 if fountain else 1
    params = {
        'read_size': read_size,
        'read_count': read_count,
    }
    return estream, params


def encode_iter(src_data, ecc, fountain):
    estream, params = _get_encoder_stream(src_data, ecc, fountain)
    with estream as instream, bit_file(instream, bits_per_op=bits_per_op(), **params) as f:
        frame_num = 0
        while f.read_count > 0:
            cells = cell_positions(CELL_SPACING, CELL_DIMENSIONS, CELLS_OFFSET)
            for x, y in interleave(cells, INTERLEAVE_BLOCKS, INTERLEAVE_PARTITIONS):
                bits = f.read()
                yield bits, x, y, frame_num
            frame_num += 1


def encode(src_data, dst_image, dark=False, ecc=ECC, fountain=False):
    def save_frame(img, frame):
        if img:
            name = dst_image if not frame else f'{dst_image}.{frame}.png'
            img.save(name)

    img = None
    frame = None
    ct = CimbEncoder(dark, symbol_bits=BITS_PER_SYMBOL, color_bits=BITS_PER_COLOR)
    for bits, x, y, frame_num in encode_iter(src_data, ecc, fountain):
        if frame != frame_num:  # save
            save_frame(img, frame)
            img = _get_image_template(TOTAL_SIZE, dark)
            frame = frame_num

        encoded = ct.encode(bits)
        img.paste(encoded, (x, y))
    save_frame(img, frame)


def main():
    args = docopt(__doc__, version='cimbar 0.0.2')

    global BITS_PER_COLOR
    BITS_PER_COLOR = int(args.get('--colorbits'))

    dark = args['--dark'] or not args['--light']
    ecc = int(args.get('--ecc'))
    fountain = bool(args.get('--fountain'))

    if args['--encode']:
        src_data = args['<src_data>'] or args['--src_data']
        dst_image = args['<output>'] or args['--output']
        encode(src_data, dst_image, dark, ecc, fountain)
        return

    deskew = get_deskew_params(args.get('--deskew'))
    should_preprocess = int(args.get('--preprocess'))
    color_correct = int(args['--color-correct'])
    src_images = args['<IMAGES>']
    dst_data = args['<output>'] or args['--output']
    decode(src_images, dst_data, dark, ecc, fountain, should_preprocess, color_correct, **deskew)


if __name__ == '__main__':
    main()
