from os import path

import numpy
import imagehash
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie1976
from colormath.color_objects import LabColor, sRGBColor
from PIL import Image


CIMBAR_ROOT = path.abspath(path.join(path.dirname(path.realpath(__file__)), '..', '..'))


def possible_colors(dark):
    if dark:
        color2 = (0xFF, 0xFF, 0, 0xFF)  # yellow is rough in light mode
    else:
        color2 = (0, 0, 0xFF, 0xFF)  # blue is rough in dark mode...
    colors = [
        (0, 0xFF, 0xFF, 0xFF),
        color2,
        (0xFF, 0, 0xFF, 0xFF),
        (0, 0xFF, 0, 0xFF),
        (0xFF, 0x7F, 0, 0xFF),  # orange
        (0, 0x7F, 0xFF, 0xFF),  # sky blue
        (0xFF, 0, 0, 0xFF),
        (0x7F, 0, 0xFF, 0xFF),  # purple
        (0xFF, 0, 0x7F, 0xFF),  # pink ... could potentally swap ff0000 for this?
        (0x7F, 0xFF, 0, 0xFF),  # lime green ... greens tend to look way too similar, and may not be reliable
        (0, 0xFF, 0x7F, 0xFF),  # sea green or something
    ]
    return colors


def load_tile(name, dark, replacements={}):
    img = Image.open(name)
    if dark:
        replacements[(255, 255, 255, 255)] = (0, 0, 0, 255)

    pixdata = img.load()
    width, height = img.size
    for y in range(height):
        for x in range(width):
            for current_color, desired_color in replacements.items():
                if pixdata[x, y] == current_color:
                    pixdata[x, y] = desired_color
                    break
    return img


class CimbDecoder:
    def __init__(self, dark, symbol_bits, color_bits=0):
        self.dark = dark
        self.symbol_bits = symbol_bits
        self.hashes = {}

        all_colors = possible_colors(dark)
        self.colors = {c: self._lab_color(all_colors[c]) for c in range(2 ** color_bits)}

        for i in range(2 ** symbol_bits):
            name = path.join(CIMBAR_ROOT, 'bitmap', f'{symbol_bits}', f'{i:02x}.png')
            img = load_tile(name, self.dark)
            ahash = imagehash.average_hash(img)
            self.hashes[i] = ahash

    def get_best_fit(self, cell_hash):
        min_distance = 1000
        best_fit = 0
        for i, ihash in self.hashes.items():
            distance = cell_hash - ihash
            if distance < min_distance:
                min_distance = distance
                best_fit = i
                if min_distance == 0:
                    break
        #if min_distance > 0:
        #    print(f'min distance is {min_distance}. best fit {best_fit}')
        return best_fit, min_distance

    def decode_symbol(self, img_cell):
        cell_hash = imagehash.average_hash(img_cell)
        return self.get_best_fit(cell_hash)  # make this return an object that knows how to get the color bits on demand???

    def _lab_color(self, c):
        rgb = sRGBColor(c[0], c[1], c[2], is_upscaled=True)
        return convert_color(rgb, LabColor)

    def _check_color(self, lab, c):
        return delta_e_cie1976(lab, self._lab_color(c))

    def _fix_color(self, c, adjust):
        return int(c * adjust)

    def _best_color(self, r, g, b):
        # probably some scaling will be good.
        max_val = max(r, g, b, 1)
        adjust = 255 / max_val
        r = self._fix_color(r, adjust)
        g = self._fix_color(g, adjust)
        b = self._fix_color(b, adjust)

        best_fit = 0
        best_distance = 1000000

        for i, c in self.colors.items():
            diff = self._check_color(c, (r, g, b))
            if diff < best_distance:
                best_fit = i
                best_distance = diff
                #if best_distance < 30:
                #    break
        return best_fit

    def decode_color(self, img_cell):
        if len(self.colors) <= 1:
            return 0

        nim = numpy.array(img_cell)
        w,h,d = nim.shape
        nim.shape = (w*h, d)
        r, g, b = tuple(nim.mean(axis=0))
        bits = self._best_color(r, g, b)
        return bits << self.symbol_bits


class CimbEncoder:
    def __init__(self, dark, symbol_bits, color_bits=0):
        self.img = {}
        self.colors = {}

        all_colors = possible_colors(dark)
        num_symbols = 2 ** symbol_bits
        for c in range(2 ** color_bits):
            color = all_colors[c]
            for i in range(num_symbols):
                name = path.join(CIMBAR_ROOT, 'bitmap', f'{symbol_bits}', f'{i:02x}.png')
                self.img[c * num_symbols + i] = self._load_img(name, dark, color)

    def _load_img(self, name, dark, color):
        # replace by color...
        replacements = {
            (0, 255, 255, 255): color,
        }
        return load_tile(name, dark, replacements)

    def encode(self, bits):
        return self.img[bits]


class cell_drift:
    pairs = [(0, 0), (1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]

    def __init__(self, limit=2):
        self.x = 0
        self.y = 0
        self.limit = limit

    def update(self, dx, dy):
        self.x += dx
        self.y += dy
        self._enforce_limit()

    def _enforce_limit(self):
        if self.x > self.limit:
            self.x = self.limit
        elif self.x < 0-self.limit:
            self.x = 0-self.limit
        if self.y > self.limit:
            self.y = self.limit
        elif self.y < 0-self.limit:
            self.y = 0-self.limit


def cell_positions(spacing, dimensions, offset=0, marker_size=6):
    '''
    ex: if dimensions == 128, and marker_size == 8:
    8 tiles at top is 128-16 == 112
    8 tiles at bottom is also 128-16 == 112

    structure would be:
    112 * 8
    128 * 112
    112 * 8
    '''
    #cells = dimensions * dimensions
    offset_y = offset
    marker_offset_x = spacing * marker_size
    top_width = dimensions - marker_size - marker_size
    top_cells = top_width * marker_size

    positions = []
    for i in range(top_cells):
        x = (i % top_width) * spacing + marker_offset_x + offset
        y = (i // top_width) * spacing + offset_y
        positions.append((x, y))

    mid_y = marker_size * spacing
    mid_width = dimensions
    mid_cells = mid_width * top_width  # top_width is also "mid_height"
    for i in range(mid_cells):
        x = (i % mid_width) * spacing + offset
        y = (i // mid_width) * spacing + mid_y + offset_y
        positions.append((x, y))

    bottom_y = (dimensions - marker_size) * spacing
    bottom_width = top_width
    bottom_cells = bottom_width * marker_size
    for i in range(bottom_cells):
        x = (i % bottom_width) * spacing + marker_offset_x + offset
        y = (i // bottom_width) * spacing + bottom_y + offset_y
        positions.append((x, y))

    return positions
