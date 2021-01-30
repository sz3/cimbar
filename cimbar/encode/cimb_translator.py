from os import path

import numpy
import imagehash
from PIL import Image


CIMBAR_ROOT = path.abspath(path.join(path.dirname(path.realpath(__file__)), '..', '..'))
DEFAULT_COLOR_CORRECT = {'r_min': 0, 'r_max': 255.0, 'g_min': 0, 'g_max': 255.0, 'b_min': 0, 'b_max': 255.0}


def possible_colors(dark, bits=0):
    if not dark:
        colors = [
            (0, 0, 0),
            (0xFF, 0, 0xFF),  # magenta
            (0, 0, 0xFF),
            (0, 0xFF, 0xFF),  # cyan
            (0xFF, 0, 0),
            (0xFF, 0x9F, 0),  # orange
            (0x7F, 0, 0xFF),  # purple
            (0, 0xFF, 0),
        ]
    elif dark and bits < 3:
        colors = [
            (0, 0xFF, 0xFF),
            (0xFF, 0xFF, 0),
            (0xFF, 0, 0xFF),
            (0, 0xFF, 0),
        ]
    else:  # dark and bits == 3
        colors = [
            (0, 0xFF, 0xFF),  # cyan
            (0x7F, 0x7F, 0xFF),  # mid-blue
            (0xFF, 0, 0xFF),  # magenta
            (0xFF, 65, 65),  # red
            (0xFF, 0x9F, 0),  # orange
            (0xFF, 0xFF, 0),  # yellow
            (0xFF, 0xFF, 0xFF),
            (0, 0xFF, 0),
            (0x9F, 0, 0xFF),  # purple
            (0xFF, 0, 0x7F),  # pink ... could potentally swap ff0000 for this?
            (0x7F, 0xFF, 0),  # lime green ... greens tend to look way too similar, and may not be reliable
            (0, 0xFF, 0x7F),  # sea green or something
        ]
    return colors[:2**bits]


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


def avg_color(img):
    nim = numpy.array(img)
    w,h,d = nim.shape
    nim.shape = (w*h, d)
    return tuple(nim.mean(axis=0))


def simple_color_scale(r, g, b):
    m = max(r, g, b, 1)
    scale = 255 / m
    return r * scale, g * scale, b * scale


def relative_color(c):
    r, g, b = c
    rg = r - g
    gb = g - b
    br = b - r
    return rg, gb, br


def relative_color_diff(c1, c2):
    rel1 = relative_color(c1)
    rel2 = relative_color(c2)
    return (rel1[0] - rel2[0])**2 + (rel1[1] - rel2[1])**2 + (rel1[2] - rel2[2])**2


class CimbDecoder:
    def __init__(self, dark, symbol_bits, color_bits=0, color_correct=DEFAULT_COLOR_CORRECT, ccm=None):
        self.dark = dark
        self.symbol_bits = symbol_bits
        self.hashes = {}

        self.color_correct = color_correct
        self.ccm = ccm

        all_colors = possible_colors(dark, color_bits)
        self.colors = {c: all_colors[c] for c in range(2 ** color_bits)}
        self.color_metrics = [(4000000, None) for c in self.colors.keys()]  # list(distance, color)

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

    def _check_color(self, c, d):
        #return (c[0] - d[0])**2 + (c[1] - d[1])**2 + (c[2] - d[2])**2
        return relative_color_diff(c, d)

    def _scale_color(self, c, adjust, down):
        c = int((c - down) * adjust)
        if c > (245 - down):
            c = 255
        return c

    def _correct_all_colors(self, r, g, b):
        if self.ccm is not None:
            r, g, b = self.ccm.dot(numpy.array([r, g, b]))
        return r, g, b

    def _update_metrics(self, i, c, color_in):
        stats = self.color_metrics[i]
        real_distance = self._check_color(c, color_in)
        if real_distance < stats[0]:
            self.color_metrics[i] = (real_distance, color_in)

    def _best_color(self, r, g, b):
        r, g, b = self._correct_all_colors(r, g, b)
        color_in = (r, g, b)

        #tr, tg, tb = r, g, b  # simple_color_scale(r, g, b)
        #print(f'{[tr, tg, tb]},')

        # probably some scaling will be good.
        if self.dark:
            max_val = max(r, g, b, 1)
            min_val = min(r, g, b, 48)
            if min_val >= max_val:
                min_val = 0
            adjust = 255.0 / (max_val - min_val)
            r = self._scale_color(r, adjust, min_val)
            g = self._scale_color(g, adjust, min_val)
            b = self._scale_color(b, adjust, min_val)
        else:
            min_val = min(r, g, b)
            max_val = max(r, g, b, 1)
            if max_val - min_val < 20:
                r = g = b = 0
            else:
                adjust = 255.0 / (max_val - min_val)
                r = self._scale_color(r, adjust, min_val)
                g = self._scale_color(g, adjust, min_val)
                b = self._scale_color(b, adjust, min_val)

        best_fit = 0
        best_distance = 1000000

        for i, c in self.colors.items():
            diff = self._check_color(c, (r, g, b))
            if diff < best_distance:
                best_fit = i
                best_distance = diff

                self._update_metrics(i, c, color_in)
                #if best_distance < 30:
                #    break
        return best_fit

    def decode_color(self, img_cell):
        if len(self.colors) <= 1:
            return 0

        r, g, b = avg_color(img_cell)
        bits = self._best_color(r, g, b)
        return bits << self.symbol_bits


class CimbEncoder:
    def __init__(self, dark, symbol_bits, color_bits=0):
        self.img = {}
        self.colors = {}

        all_colors = possible_colors(dark, color_bits)
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
