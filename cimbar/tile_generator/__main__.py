import random
import time
from os import makedirs, path

from bitstring import BitStream
from PIL import Image

from cimbar.tile_generator.validator import Validator


def _path(seed):
    return '/tmp/tiles/{}'.format(seed)


def _image_template(tile_size=8):
    color = (255, 255, 255)
    img = Image.new('RGB', (tile_size, tile_size), color=color)
    return img


def _get_random_bits(how_many):
    random_int = random.getrandbits(how_many)
    return BitStream(uint=random_int, length=how_many)


def generate_tile(tile_size):
    img = _image_template()
    pixels = img.load()
    num_bits = tile_size * tile_size
    bits = _get_random_bits(num_bits)
    for i, b in enumerate(bits):
        x = i % tile_size
        y = i // tile_size
        if b:
            pixels[x, y] = (0, 255, 255)
    return img


def generate_tileset(seed, num_tiles=16):
    start_time = time.time()
    random.seed(seed)
    dir_path = _path(seed)
    makedirs(dir_path, exist_ok=True)

    v = Validator()
    count = 0
    for t in range(num_tiles):
        tile_path = path.join(dir_path, f'{t:02x}.png')
        if path.exists(tile_path):
            print('skipping {}; already exists'.format(tile_path))
            continue

        while True:
            img = generate_tile(8)
            count += 1
            if v.add_if_valid(img):
                break
        img.save(tile_path)

    print("--- {} seconds for {} --- Needed {} iterations.".format(time.time() - start_time, seed, count))


def main():
    random.seed()
    for run in range(5):
        tileset_seed = random.getrandbits(128)
        true_random = random.getstate()
        generate_tileset(tileset_seed)
        random.setstate(true_random)


if __name__ == '__main__':
    main()