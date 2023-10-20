from collections import deque
from os import path

import numpy
import imagehash
from PIL import Image


CIMBAR_ROOT = path.abspath(path.join(path.dirname(path.realpath(__file__)), '..', '..'))
DEFAULT_COLOR_CORRECT = {'r_min': 0, 'r_max': 255.0, 'g_min': 0, 'g_max': 255.0, 'b_min': 0, 'b_max': 255.0}


class AdaptiveMetrics:
    max_deque = deque([150]*8)
    min_deque = deque([150]*8)
    red_mid = deque([100]*8)
    green_mid = deque([100]*8)
    blue_mid = deque([100]*8)
    red_max = deque([255]*8)
    green_max = deque([255]*8)
    blue_max = deque([255]*8)

    @classmethod
    def update_cutoffs(cls, r, g, b):
        minval = min(r, g, b)
        cls.min_deque.popleft()
        cls.min_deque.append(minval)

        cls.red_mid.popleft()
        cls.red_mid.append(r)
        cls.green_mid.popleft()
        cls.green_mid.append(g)
        cls.blue_mid.popleft()
        cls.blue_mid.append(b)

    @classmethod
    def update_rgb_max(cls, r, g, b):
        maxval = max(r, g, b)
        cls.max_deque.popleft()
        cls.max_deque.append(maxval)

        cls.red_max.popleft()
        cls.red_max.append(r)
        cls.green_max.popleft()
        cls.green_max.append(g)
        cls.blue_max.popleft()
        cls.blue_max.append(b)

    @classmethod
    def color_cutoff(cls):
        return min(cls.max_deque) / 2.25

    @classmethod
    def low(cls):
        return min(cls.min_deque)

    @classmethod
    def high(cls):
        return max(cls.max_deque)

    @classmethod
    def low_red(cls):
        return min(cls.red_mid)

    @classmethod
    def high_red(cls):
        return max(cls.red_max)

    @classmethod
    def low_green(cls):
        return min(cls.green_mid)

    @classmethod
    def high_green(cls):
        return max(cls.green_max)

    @classmethod
    def low_blue(cls):
        return min(cls.blue_mid)

    @classmethod
    def high_blue(cls):
        return max(cls.blue_max)


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
            (0, 0xFF, 0),
            (0, 0xFF, 0xFF),
            (0xFF, 0xFF, 0),
            (0xFF, 0, 0xFF),
        ]
    else:  # dark and bits == 3 (>=??)
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


def update_metric(key, val):
    global _ADAPTIVE_METRICS
    _ADAPTIVE_METRICS[key] = val


def avg_color(img, dark):
    nim = numpy.array(img)
    w,h,d = nim.shape
    nim.shape = (w*h, d)

    cutoff = AdaptiveMetrics.color_cutoff()
    if dark:
        nim = numpy.array([(r,g,b) for r,g,b in nim if r > cutoff or g > cutoff or b > cutoff])
        if len(nim) <= 3:
            nim = numpy.array(img)
            nim.shape = (w*h, d)

    # save the max value for r,g,b as well
    # we'll use the min(max) as a proxy for the lowest r,g,b values possible
    return tuple(nim.mean(axis=0)), tuple(nim.max(axis=0))


def simple_color_scale(r, g, b):
    m = max(r, g, b, 1)
    scale = 255 / m
    return r * scale, g * scale, b * scale


def min_max_scale(min_val, max_val):
    if min_val >= max_val:
        min_val = 0
    return 255.0 / (max_val - min_val)


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
        self.color_metrics = []
        self.color_clusters = None

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
        if c > 245:
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

    def best_color(self, rgb_mean, rgb_max):
        r, g, b = rgb_mean
        r, g, b = self._correct_all_colors(r, g, b)
        #print(f'{r} {g} {b}')

        metrics = [
            r, g, b, rgb_max[0], rgb_max[1], rgb_max[2],
            AdaptiveMetrics.low_red(), AdaptiveMetrics.low_green(), AdaptiveMetrics.low_blue(),
            AdaptiveMetrics.high_red(), AdaptiveMetrics.high_green(), AdaptiveMetrics.high_blue(),
            AdaptiveMetrics.low(), AdaptiveMetrics.high()
        ]
        metrics = [str(m) for m in metrics]
        print(','.join(metrics))
        AdaptiveMetrics.update_cutoffs(r,g,b)
        AdaptiveMetrics.update_rgb_max(*rgb_max)

        # probably some scaling will be good.
        if self.dark:
            max_val = max(r, g, b, 1)
            #print(f'low is {AdaptiveMetrics.low()}')
            min_val = min(r, g, b, AdaptiveMetrics.low())  # 48
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

        color_in = (r, g, b)
        self.color_metrics.append(color_in)
        if self.color_clusters:
            return self.color_clusters.categorize(color_in)

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

        rgb_mean, rgb_max = avg_color(img_cell, self.dark)
        # count colors?
        bits = self.best_color(rgb_mean, rgb_max)
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

