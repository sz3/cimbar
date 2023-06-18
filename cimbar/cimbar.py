#!/usr/bin/python3

"""color-icon-matrix barcode

Usage:
  ./cimbar.py <IMAGES>... --output=<filename> [--config=<sq8x8,sq5x5,sq5x6>] [--dark | --light]
                         [--colorbits=<0-3>] [--deskew=<0-2>] [--ecc=<0-200>]
                         [--fountain] [--preprocess=<0,1>] [--color-correct]
  ./cimbar.py --encode (<src_data> | --src_data=<filename>) (<output> | --output=<filename>)
                       [--config=<sq8x8,sq5x5,sq5x6>] [--dark | --light]
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
  -e --ecc=<0-200>                 Reed solomon error correction level. 0 is no ecc. [default: auto]
  -f --fountain                    Use fountain encoding scheme.
  --config=<config>                Choose configuration from sq8x8,sq5x5,sq5x6. [default: sq8x8]
  --dark                           Use dark palette. [default]
  --light                          Use light palette.
  --color-correct                  Attempt color correction.
  --deskew=<0-2>                   Deskew level. 0 is no deskew. Should usually be 0 or default. [default: 1]
  --preprocess=<0,1>               Sharpen image before decoding. Default is to guess. [default: -1]
"""
from os import path
from tempfile import TemporaryDirectory

import cv2
import numpy
from docopt import docopt
from PIL import Image

from cimbar import conf
from cimbar.deskew.deskewer import deskewer
from cimbar.encode.cell_positions import cell_positions, AdjacentCellFinder, FloodDecodeOrder
from cimbar.encode.cimb_translator import CimbEncoder, CimbDecoder, avg_color
from cimbar.encode.rss import reed_solomon_stream
from cimbar.util.bit_file import bit_file
from cimbar.util.interleave import interleave, interleave_reverse, interleaved_writer


BITS_PER_COLOR=conf.BITS_PER_COLOR


def get_deskew_params(level):
    level = int(level)
    return {
        'deskew': level,
        'auto_dewarp': level >= 2,
    }


def bits_per_op():
    return conf.BITS_PER_SYMBOL + BITS_PER_COLOR


def num_cells():
    return conf.CELL_DIM_Y*conf.CELL_DIM_X - (conf.MARKER_SIZE_X*conf.MARKER_SIZE_Y * 4)


def capacity(bits_per_op=bits_per_op()):
    return num_cells() * bits_per_op // 8;


def _fountain_chunk_size(ecc=conf.ECC, bits_per_op=bits_per_op(), fountain_blocks=conf.FOUNTAIN_BLOCKS):
    return capacity(bits_per_op) * (conf.ECC_BLOCK_SIZE-ecc) // conf.ECC_BLOCK_SIZE // fountain_blocks


def detect_and_deskew(src_image, temp_image, dark, auto_dewarp=False):
    return deskewer(src_image, temp_image, dark, auto_dewarp=auto_dewarp)


def _decode_cell(ct, img, color_img, x, y, drift):
    best_distance = 1000
    for dx, dy in drift.pairs:
        testX = x + drift.x + dx
        testY = y + drift.y + dy
        img_cell = img.crop((testX, testY, testX + conf.CELL_SIZE, testY + conf.CELL_SIZE))
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
    best_cell = color_img.crop((testX+1, testY+1, testX + conf.CELL_SIZE-1, testY + conf.CELL_SIZE-1))
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
    return reed_solomon_stream(f, ecc, conf.ECC_BLOCK_SIZE, mode='write', on_failure=on_rss_failure) if ecc else f


def compute_tint(img, dark):
    def update(c, r, g, b):
        c['r'] = max(c['r'], r)
        c['g'] = max(c['g'], g)
        c['b'] = max(c['b'], b)

    cc = {}
    cc['r'] = cc['g'] = cc['b'] = 1

    if dark:
        pos = [(28, 28), (28, conf.TOTAL_SIZE-32), (conf.TOTAL_SIZE-32, 28)]
    else:
        pos = [(67, 0), (0, 67), (conf.TOTAL_SIZE-79, 0), (0, conf.TOTAL_SIZE-79)]

    for x, y in pos:
        iblock = img.crop((x, y, x + 4, y + 4))
        r, g, b = avg_color(iblock)
        update(cc, *avg_color(iblock))

    print(f'tint is {cc}')
    return cc['r'], cc['g'], cc['b']


def _decode_iter(ct, img, color_img):
    cell_pos, num_edge_cells = cell_positions(conf.CELL_SPACING_X, conf.CELL_SPACING_Y, conf.CELL_DIM_X,
                                              conf.CELL_DIM_Y, conf.CELLS_OFFSET, conf.MARKER_SIZE_X, conf.MARKER_SIZE_Y)
    finder = AdjacentCellFinder(cell_pos, num_edge_cells, conf.CELL_DIM_X, conf.MARKER_SIZE_X)
    decode_order = FloodDecodeOrder(cell_pos, finder)
    for i, (x, y), drift in decode_order:
        best_bits, best_dx, best_dy, best_distance = _decode_cell(ct, img, color_img, x, y, drift)
        decode_order.update(best_dx, best_dy, best_distance)
        yield i, best_bits


def decode_iter(src_image, dark, should_preprocess, should_color_correct, deskew, auto_dewarp):
    tempdir = None
    if deskew:
        tempdir = TemporaryDirectory()
        temp_img = path.join(tempdir.name, path.basename(src_image))
        dims = detect_and_deskew(src_image, temp_img, dark, auto_dewarp)
        if should_preprocess < 0:
            should_preprocess = dims[0] < conf.TOTAL_SIZE or dims[1] < conf.TOTAL_SIZE
        color_img = Image.open(temp_img)
    else:
        color_img = Image.open(src_image)

    ct = CimbDecoder(dark, symbol_bits=conf.BITS_PER_SYMBOL, color_bits=conf.BITS_PER_COLOR)
    img = _preprocess_for_decode(color_img) if should_preprocess else color_img

    if should_color_correct:
        from colormath.chromatic_adaptation import _get_adaptation_matrix
        ct.ccm = _get_adaptation_matrix(numpy.array([*compute_tint(color_img, dark)]),
                                        numpy.array([255, 255, 255]), 2, 'von_kries')

    yield from _decode_iter(ct, img, color_img)

    if tempdir:  # cleanup
        with tempdir:
            pass


def decode(src_images, outfile, dark=False, ecc=conf.ECC, fountain=False, force_preprocess=False, color_correct=False,
           deskew=True, auto_dewarp=False):
    cells, _ = cell_positions(conf.CELL_SPACING_X, conf.CELL_SPACING_Y, conf.CELL_DIM_X, conf.CELL_DIM_Y,
                              conf.CELLS_OFFSET, conf.MARKER_SIZE_X, conf.MARKER_SIZE_Y)
    interleave_lookup, block_size = interleave_reverse(cells, conf.INTERLEAVE_BLOCKS, conf.INTERLEAVE_PARTITIONS)
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
    estream = reed_solomon_stream(f, ecc, conf.ECC_BLOCK_SIZE) if ecc else f

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
            cells, _ = cell_positions(conf.CELL_SPACING_X, conf.CELL_SPACING_Y, conf.CELL_DIM_X, conf.CELL_DIM_Y,
                                      conf.CELLS_OFFSET, conf.MARKER_SIZE_X, conf.MARKER_SIZE_Y)
            assert len(cells) == num_cells()
            for x, y in interleave(cells, conf.INTERLEAVE_BLOCKS, conf.INTERLEAVE_PARTITIONS):
                bits = f.read()
                yield bits, x, y, frame_num
            frame_num += 1


def encode(src_data, dst_image, dark=False, ecc=conf.ECC, fountain=False):
    def save_frame(img, frame):
        if img:
            name = dst_image if not frame else f'{dst_image}.{frame}.png'
            img.save(name)

    img = None
    frame = None
    ct = CimbEncoder(dark, symbol_bits=conf.BITS_PER_SYMBOL, color_bits=BITS_PER_COLOR)
    for bits, x, y, frame_num in encode_iter(src_data, ecc, fountain):
        if frame != frame_num:  # save
            save_frame(img, frame)
            img = _get_image_template(conf.TOTAL_SIZE, dark)
            frame = frame_num

        encoded = ct.encode(bits)
        img.paste(encoded, (x, y))
    save_frame(img, frame)


def main():
    args = docopt(__doc__, version='cimbar 0.5.13')

    global BITS_PER_COLOR
    BITS_PER_COLOR = int(args.get('--colorbits'))

    config = args['--config']
    if config:
        config = conf.known[config]
        conf.init(config)
    dark = args['--dark'] or not args['--light']
    try:
        ecc = int(args.get('--ecc'))
    except:
        ecc = conf.ECC
    fountain = bool(args.get('--fountain'))

    if args['--encode']:
        src_data = args['<src_data>'] or args['--src_data']
        dst_image = args['<output>'] or args['--output']
        encode(src_data, dst_image, dark, ecc, fountain)
        return

    deskew = get_deskew_params(args.get('--deskew'))
    should_preprocess = int(args.get('--preprocess'))
    color_correct = args['--color-correct']
    src_images = args['<IMAGES>']
    dst_data = args['<output>'] or args['--output']
    decode(src_images, dst_data, dark, ecc, fountain, should_preprocess, color_correct, **deskew)


if __name__ == '__main__':
    main()

