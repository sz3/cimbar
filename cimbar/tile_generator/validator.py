import imagehash
from PIL import ImageFilter, ImageChops, ImageDraw, ImageOps


class ImageCompare:
    hash_dist = 30

    def __init__(self):
        self.hashes = set()

    @property
    def count(self):
        return len(self.hashes)

    def is_valid(self, new_tile):
        thash = self.process(new_tile)
        for h in self.hashes:
            if h - thash < self.hash_dist:
                return False
        return True

    def hash_fun(self, img):
        return imagehash.average_hash(img)

    def add(self, new_tile):
        thash = self.process(new_tile)
        self.hashes.add(thash)

    def process(self, new_tile):
        raise NotImplementedError()


class AverageHash(ImageCompare):
    def process(self, new_tile):
        return self.hash_fun(new_tile)


class BlurryHash(ImageCompare):
    hash_dist = 30

    def process(self, new_tile):
        blurred = new_tile.filter(ImageFilter.SMOOTH)
        return self.hash_fun(blurred)


class VeryBlurryHash(ImageCompare):
    hash_dist = 25

    def process(self, new_tile):
        blurred = new_tile.filter(ImageFilter.BoxBlur(1))
        return self.hash_fun(blurred)


class DownSizeHash(ImageCompare):
    hash_dist = 25

    def __init__(self, size, **kwargs):
        super().__init__(**kwargs)
        self.size = size

    def process(self, new_tile):
        img = new_tile.resize((self.size, self.size))
        return self.hash_fun(img)


class OffsetHash(ImageCompare):
    hash_dist = 25

    def __init__(self, x=1, y=1, **kwargs):
        super().__init__(**kwargs)
        self.x = x
        self.y = y

    def process(self, new_tile):
        off = ImageChops.offset(new_tile, self.x, self.y)
        xline = (0,0) + (0,8) if self.x > 0 else (7,0) + (7,8)
        yline = (0,0) + (8,0) if self.y > 0 else (0,7) + (8,7)
        od = ImageDraw.Draw(off)
        od.line(xline, fill=255)
        od.line(yline, fill=255)
        return self.hash_fun(off)


class CropHash(ImageCompare):
    hash_dist = 25

    def process(self, new_tile):
        img = ImageOps.crop(new_tile, border=1)
        return self.hash_fun(img)


class Validator:
    def __init__(self):
        self.hashers = [
            AverageHash(),
            CropHash(),
            DownSizeHash(6),
            DownSizeHash(4),
            BlurryHash(),
            VeryBlurryHash(),
            OffsetHash(1, 1),
            OffsetHash(1, -1),
            OffsetHash(-1, 1),
            OffsetHash(-1, -1),
        ]

    def add_if_valid(self, new_tile):
        for h in self.hashers:
            if not h.is_valid(new_tile):
                return False

        for h in self.hashers:
            h.add(new_tile)
        return True
