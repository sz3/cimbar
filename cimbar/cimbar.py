#!/usr/bin/python3

"""color-icon-matrix barcode

Usage:
  ./cimbar.py <IMAGES>... --output=<filename> [--config=<sq8x8,sq5x5,sq5x6>] [--dark | --light]
                         [--colorbits=<0-3>] [--deskew=<0-2>] [--ecc=<0-200>]
                         [--fountain] [--preprocess=<0,1>] [--color-correct=<0-2>]
  ./cimbar.py --encode (<src_data> | --src_data=<filename>) (<output> | --output=<filename>)
                       [--config=<sq8x8,og8x8,sq5x5,sq5x6>] [--dark | --light]
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
  --color-correct=<0-2>            Color correction. 0 is off. 1 is white balance. 2 is 2-pass least squares. [default: 1]
  --deskew=<0-2>                   Deskew level. 0 is no deskew. Should usually be 0 or default. [default: 1]
  --preprocess=<0,1>               Sharpen image before decoding. Default is to guess. [default: -1]
"""
from collections import defaultdict
from io import BytesIO
from os import path
from tempfile import TemporaryDirectory

import cv2
import numpy
from docopt import docopt
from PIL import Image

from cimbar import conf
from cimbar.deskew.deskewer import deskewer
from cimbar.encode.cell_positions import cell_positions, AdjacentCellFinder, FloodDecodeOrder
from cimbar.encode.cimb_translator import CimbEncoder, CimbDecoder, avg_color, possible_colors
from cimbar.encode.rss import reed_solomon_stream
from cimbar.fountain.header import fountain_header
from cimbar.util.bit_file import bit_file
from cimbar.util.interleave import interleave, interleave_reverse, interleaved_writer
from cimbar.util.clustering import ClusterSituation


BITS_PER_COLOR=conf.BITS_PER_COLOR


def get_deskew_params(level):
    level = int(level)
    return {
        'deskew': level,
        'auto_dewarp': level >= 2,
    }


def bits_per_op():
    return conf.BITS_PER_SYMBOL + BITS_PER_COLOR


def use_split_mode():
    return getattr(conf, 'SPLIT_MODE', True)


def num_cells():
    return conf.CELL_DIM_Y*conf.CELL_DIM_X - (conf.MARKER_SIZE_X*conf.MARKER_SIZE_Y * 4)


def num_fountain_blocks():
    return bits_per_op() * 2


def capacity(bits_per_op=bits_per_op()):
    return num_cells() * bits_per_op // 8;


def _fountain_chunk_size(ecc=conf.ECC, bits_per_op=bits_per_op(), fountain_blocks=conf.FOUNTAIN_BLOCKS):
    fountain_blocks = fountain_blocks or num_fountain_blocks()
    return capacity(bits_per_op) * (conf.ECC_BLOCK_SIZE-ecc) // conf.ECC_BLOCK_SIZE // fountain_blocks


def _get_expected_fountain_headers(headers, bits_per_symbol=conf.BITS_PER_SYMBOL, bits_per_color=BITS_PER_COLOR):
    import bitstring
    from bitstring import Bits, BitStream

    # it'd be nice to use the frame id as well, but sometimes we skip frames.
    # specifically, at the end of the input data (so when num_cunks*chunk size ~= file size)
    # we will usually skip a frame (whenever the last chunk is not conveniently equal to the frame size)
    # we *could* do that math and use the frame id anyway, it might be worth it...
    for header in headers:
        if not header.bad():
            break
    assert not header.bad()  # TODO: maybe just return NULL?

    color_headers = []
    for _ in range(bits_per_color * 2):
        color_headers += bytes(header)[:-2]  # remove frame id

    print(color_headers)

    res = []
    stream = BitStream()
    stream.append(Bits(bytes=color_headers))
    while stream.pos < stream.length:
        res.append(stream.read(f'uint:{bits_per_color}'))
    return res


def _get_fountain_header_cell_index(cells, expected_vals):
    # TODO: misleading to say this works for all FOUNTAIN_BLOCKS values...
    fountain_blocks = conf.FOUNTAIN_BLOCKS or num_fountain_blocks()
    end = capacity(BITS_PER_COLOR) * 8 // BITS_PER_COLOR
    header_start_interval = capacity(bits_per_op()) * 8 // fountain_blocks // BITS_PER_COLOR
    header_len = (fountain_header.length-2) * 8 // BITS_PER_COLOR

    cell_idx = []
    i = 0
    while i < end:
        # maybe split this into a list of lists? idk
        cell_idx += list(range(i, i+header_len))
        i += header_start_interval

    # sanity check, we're doomed if this fails
    assert len(cell_idx) == len(expected_vals), f'{len(cell_idx)} == {len(expected_vals)}'
    res = defaultdict(list)
    for idx,exp in zip(cell_idx, expected_vals):
        res[exp].append(cells[idx])
    return res


def _build_color_decode_lookups(ct, color_img, color_map):
    res = defaultdict(list)
    for exp, pos_list in color_map.items():
        for pos in pos_list:
            cell = _crop_cell(color_img, pos[0], pos[1])
            color = avg_color(cell, dark=ct.dark)
            res[exp].append(color)
            bits = ct.decode_color(cell, 0)
            if bits != exp:
                print(f' wrong!!! {pos} ... {bits} == {exp}')

    # return averages
    return {
        k: tuple(numpy.mean(vals, axis=0)) for k,vals in res.items()
    }


def _decode_sector_calc(midpt, x, y, num_sectors):
    if num_sectors < 2:
        return 0
    if (x - midpt[0])**2 + (y - midpt[1])**2 < 400**2:
        return 0
    else:
        return 1


def _derive_color_lookups(ct, color_img, cells, fount_headers, splits=0):
    header_cell_locs = _get_fountain_header_cell_index(
        list(interleave(cells, conf.INTERLEAVE_BLOCKS, conf.INTERLEAVE_PARTITIONS)),
        _get_expected_fountain_headers(fount_headers),
    )
    print(header_cell_locs)

    color_maps = []
    if splits == 2:
        center_map = defaultdict(list)
        edge_map = defaultdict(list)
        midX = conf.TOTAL_SIZE // 2
        midY = conf.TOTAL_SIZE // 2
        for exp,pos in header_cell_locs.items():
            for xy in pos:
                if _decode_sector_calc((midX, midY), *xy, splits) == 0:
                    center_map[exp].append(xy)
                else:
                    edge_map[exp].append(xy)

        lc = {exp: len(pos) for exp, pos in center_map.items()}
        le = {exp: len(pos) for exp, pos in edge_map.items()}
        print(f'sanity check. len(center)={lc}, len(edge)={le}')
        color_maps = [center_map, edge_map]

    else:
        color_map = dict()
        for exp,pos in header_cell_locs.items():
            color_map[exp] = pos
        color_maps = [color_map]

    return [_build_color_decode_lookups(ct, color_img, cm) for cm in color_maps]


def detect_and_deskew(src_image, temp_image, dark, auto_dewarp=False):
    return deskewer(src_image, temp_image, dark, auto_dewarp=auto_dewarp)


def _decode_cell(ct, img, x, y, drift):
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
    best_cell = (testX, testY)
    return best_bits, best_cell, best_dx, best_dy, best_distance


def _preprocess_for_decode(img):
    ''' This might need to be conditional based on source image size.'''
    img = cv2.cvtColor(numpy.array(img), cv2.COLOR_RGB2BGR)
    #kernel = numpy.array([[-1.0,-1.0,-1.0], [-1.0,8.5,-1.0], [-1.0,-1.0,-1.0]])
    #img = cv2.filter2D(img, -1, kernel)
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

    stream = reed_solomon_stream(f, ecc, conf.ECC_BLOCK_SIZE, mode='write', on_failure=on_rss_failure) if ecc else f
    fount = f if fountain else None
    return stream, fount


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
        r, g, b = avg_color(iblock, False)
        update(cc, *avg_color(iblock, False))

    print(f'tint is {cc}')
    return cc['r'], cc['g'], cc['b']


def _crop_cell(img, x, y):
    return img.crop((x+1, y+1, x + conf.CELL_SIZE-1, y + conf.CELL_SIZE-1))


def _decode_symbols(ct, img):
    cell_pos, num_edge_cells = cell_positions(conf.CELL_SPACING_X, conf.CELL_SPACING_Y, conf.CELL_DIM_X,
                                              conf.CELL_DIM_Y, conf.CELLS_OFFSET, conf.MARKER_SIZE_X, conf.MARKER_SIZE_Y)
    finder = AdjacentCellFinder(cell_pos, num_edge_cells, conf.CELL_DIM_X, conf.MARKER_SIZE_X)
    decode_order = FloodDecodeOrder(cell_pos, finder)
    print('beginning decode symbols pass...')
    for i, (x, y), drift in decode_order:
        best_bits, best_cell, best_dx, best_dy, best_distance = _decode_cell(ct, img, x, y, drift)
        decode_order.update(best_dx, best_dy, best_distance)
        yield i, best_bits, best_cell


def _calc_ccm(ct, color_lookups, cc_setting):
    splits = 2 if cc_setting in (6, 7) else 0
    if cc_setting in (3, 4, 5):
        possible = possible_colors(ct.dark, BITS_PER_COLOR)
        #if len(color_lookups[0]) < len(possible):
        #    return
        exp = [color for i,color in enumerate(possible) if i in color_lookups[0]]
        exp = numpy.array(exp)
        observed = numpy.array([v for k,v in sorted(color_lookups[0].items())])
        from colour.characterisation.correction import matrix_colour_correction_Cheung2004
        der = matrix_colour_correction_Cheung2004(observed, exp)

        # not sure which of this would be better...
        if ct.ccm is None or cc_setting == 4:
            ct.ccm = der
        else:  # cc_setting == 3,5
            ct.ccm = der.dot(ct.ccm)

    if splits:
        from colour.characterisation.correction import matrix_colour_correction_Cheung2004
        exp = numpy.array(possible_colors(ct.dark, BITS_PER_COLOR))
        ccms = list()
        i = 0
        while i < splits:
            observed = numpy.array([v for k,v in sorted(color_lookups[i].items())])
            der = matrix_colour_correction_Cheung2004(observed, exp)
            ccms.append(der)
            i += 1

        if ct.ccm is None or cc_setting == 7:
            ct.ccm = ccms
        else:
            ct.ccm = [der.dot(ct.ccm) for der in ccms]


def _decode_iter(ct, img, color_img, state_info={}):
    decoding = sorted(_decode_symbols(ct, img))
    if use_split_mode():
        for i, bits, _ in decoding:
            yield i, bits
        yield -1, None

    # state_info can be set at any time, but it will probably be set by the caller *after* the empty yield above
    if state_info.get('headers'):
        print('now would be a good time to use the color index')
        cc_setting = state_info['color_correct']
        splits = 2 if cc_setting in (6, 7) else 0

        cells = [cell for _, __, cell in decoding]
        color_lookups = _derive_color_lookups(ct, color_img, cells, state_info.get('headers'), splits)
        print('color lookups:')
        print(color_lookups)

        #matrix_colour_correction_Cheung2004
        #matrix_colour_correction_Finlayson2015

        _calc_ccm(ct, color_lookups, cc_setting)

    print('beginning decode colors pass...')
    midX = conf.TOTAL_SIZE // 2
    midY = conf.TOTAL_SIZE // 2
    for i, bits, cell in decoding:
        testX, testY = cell
        best_cell = _crop_cell(color_img, testX, testY)
        decode_sector = 0 if ct.ccm is None else _decode_sector_calc((midX, midY), testX, testY, len(ct.ccm))
        if use_split_mode():
            yield i, ct.decode_color(best_cell, 0)
        else:
            yield i, bits + (ct.decode_color(best_cell, 0) << conf.BITS_PER_SYMBOL)


def decode_iter(src_image, dark, should_preprocess, color_correct, deskew, auto_dewarp, state_info={}):
    tempdir = None
    if deskew:
        tempdir = TemporaryDirectory()
        temp_img = path.join(tempdir.name, path.basename(src_image))  # or /tmp
        dims = detect_and_deskew(src_image, temp_img, dark, auto_dewarp)
        if should_preprocess < 0:
            should_preprocess = dims[0] < conf.TOTAL_SIZE or dims[1] < conf.TOTAL_SIZE
        color_img = Image.open(temp_img)
    else:
        color_img = Image.open(src_image)

    ct = CimbDecoder(dark, symbol_bits=conf.BITS_PER_SYMBOL, color_bits=conf.BITS_PER_COLOR)
    img = _preprocess_for_decode(color_img) if should_preprocess else color_img

    if color_correct:
        from colormath.chromatic_adaptation import _get_adaptation_matrix
        ct.ccm = white = _get_adaptation_matrix(numpy.array([*compute_tint(color_img, dark)]),
                                        numpy.array([255, 255, 255]), 2, 'von_kries')
        if color_correct == 2:
            for _ in _decode_iter(ct, img, color_img):
                pass
            clusters = ClusterSituation(ct.color_metrics, 2**BITS_PER_COLOR)
            clusters.plot('/tmp/foo.png')
            clusters.index = {i: ct.best_color(*k) for i,k in enumerate(clusters.centers())}
            ct.color_clusters = clusters

            '''observed = [c for _, c in ct.color_metrics]
            exp = numpy.array(possible_colors(dark, BITS_PER_COLOR))
            from colour.characterisation.correction import matrix_colour_correction_Cheung2004
            der = matrix_colour_correction_Cheung2004(observed, exp)
            ct.ccm = der.dot(white)'''

    yield from _decode_iter(ct, img, color_img, state_info)

    if tempdir:  # cleanup
        with tempdir:
            pass


def decode(src_images, outfile, dark=False, ecc=conf.ECC, fountain=False, force_preprocess=False, color_correct=False,
           deskew=True, auto_dewarp=False):
    cells, _ = cell_positions(conf.CELL_SPACING_X, conf.CELL_SPACING_Y, conf.CELL_DIM_X, conf.CELL_DIM_Y,
                              conf.CELLS_OFFSET, conf.MARKER_SIZE_X, conf.MARKER_SIZE_Y)
    interleave_lookup, block_size = interleave_reverse(cells, conf.INTERLEAVE_BLOCKS, conf.INTERLEAVE_PARTITIONS)
    dstream, fount = _get_decoder_stream(outfile, ecc, fountain)
    dupe_stream = dupe_pass = None
    if color_correct >= 3 and not fount:
        dupe_stream, fount = _get_decoder_stream('/dev/null', ecc, True)
    with dstream as outstream:
        for imgf in src_images:
            if use_split_mode():
                first_pass = interleaved_writer(
                    f=outstream, bits_per_op=conf.BITS_PER_SYMBOL, mode='write', keep_open=True
                )
                if dupe_stream:
                    dupe_pass = interleaved_writer(
                        f=dupe_stream, bits_per_op=conf.BITS_PER_SYMBOL, mode='write', keep_open=True
                    )
                second_pass = interleaved_writer(
                    f=outstream, bits_per_op=BITS_PER_COLOR, mode='write', keep_open=True
                )
            else:
                first_pass = interleaved_writer(f=outstream, bits_per_op=bits_per_op(), mode='write', keep_open=True)
                second_pass = None

            # this is a bit goofy, might refactor it to have less "loop through writers" weirdness
            # ok, gonna *have* to rewrite it to get at + pass the fountain header anyway...
            iw = first_pass
            state_info = {}
            for i, bits in decode_iter(
                    imgf, dark, force_preprocess, color_correct, deskew, auto_dewarp, state_info
            ):
                if i == -1:
                    # flush and move to the second writer
                    with iw:
                        pass
                    if dupe_pass:
                        with dupe_pass:
                            pass
                    iw = second_pass
                    if fount:
                        state_info['headers'] = fount.headers
                        state_info['color_correct'] = color_correct
                    continue
                block = interleave_lookup[i] // block_size
                iw.write(bits, block)
                if dupe_pass:
                    dupe_pass.write(bits, block)

            # flush iw
            with iw:
                pass


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


def _get_encoder_stream(src, ecc, fountain, compression_level=16):
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

            if use_split_mode():
                symbols = []
                for x, y in interleave(cells, conf.INTERLEAVE_BLOCKS, conf.INTERLEAVE_PARTITIONS):
                    bits = f.read(conf.BITS_PER_SYMBOL)
                    symbols.append(bits)

                # there are better ways to do this than reverse+pop...
                # the important part is that it's a 2-pass approach
                symbols.reverse()

                for x, y in interleave(cells, conf.INTERLEAVE_BLOCKS, conf.INTERLEAVE_PARTITIONS):
                    bits = symbols.pop() | (f.read(BITS_PER_COLOR) << conf.BITS_PER_SYMBOL)
                    yield bits, x, y, frame_num

            else:
                for x, y in interleave(cells, conf.INTERLEAVE_BLOCKS, conf.INTERLEAVE_PARTITIONS):
                    bits = f.read()
                    yield bits, x, y, frame_num

            frame_num += 1
        print(f'encoded {frame_num} frames')


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
    args = docopt(__doc__, version='cimbar 0.6.0')

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
    color_correct = int(args.get('--color-correct'))
    src_images = args['<IMAGES>']
    dst_data = args['<output>'] or args['--output']
    decode(src_images, dst_data, dark, ecc, fountain, should_preprocess, color_correct, **deskew)


if __name__ == '__main__':
    main()

