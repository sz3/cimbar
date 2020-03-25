import imagehash
from PIL import Image


class CimbTranslator:
    def __init__(self, dark, bits):
        self.dark = dark
        self.hashes = {}
        self.img = {}
        for i in range(2 ** bits):
            name = f'bitmap/{bits}/{i:02x}.png'
            self.img[i] = self._load_img(name)
            ahash = imagehash.average_hash(self.img[i], 6)
            self.hashes[i] = ahash

    def _load_img(self, name):
        img = Image.open(name)
        if not self.dark:
            return img

        pixdata = img.load()
        width, height = img.size
        for y in range(height):
            for x in range(width):
                if pixdata[x, y] == (255, 255, 255, 255):
                    pixdata[x, y] = (0, 0, 0, 255)
        return img

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

    def decode(self, img_cell):
        cell_hash = imagehash.average_hash(img_cell, 6)
        return self.get_best_fit(cell_hash)

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


def cell_positions(spacing, dimensions, marker_size=6):
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
    marker_offset_x = spacing * marker_size
    top_width = dimensions - marker_size - marker_size
    top_cells = top_width * marker_size
    for i in range(top_cells):
        x = (i % top_width) * spacing + marker_offset_x
        y = (i // top_width) * spacing
        yield x, y

    mid_y = marker_size * spacing
    mid_width = dimensions
    mid_cells = mid_width * top_width  # top_width is also "mid_height"
    for i in range(mid_cells):
        x = (i % mid_width) * spacing
        y = (i // mid_width) * spacing + mid_y
        yield x, y

    bottom_y = (dimensions - marker_size) * spacing
    bottom_width = top_width
    bottom_cells = bottom_width * marker_size
    for i in range(bottom_cells):
        x = (i % bottom_width) * spacing + marker_offset_x
        y = (i // bottom_width) * spacing + bottom_y
        yield x, y