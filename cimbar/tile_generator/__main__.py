import random
from os import mkdir, path

from bitstring import BitStream
from PIL import Image


def _path(seed):
    return '/tmp/tiles/{}'.format(seed)


def _image_template(tile_size=8):
    color = (255, 255, 255)
    img = Image.new('RGB', (tile_size, tile_size), color=color)
    return img


def _get_random_bits(how_many):
    random_int = random.getrandbits(how_many)
    return BitStream(uint=random_int, length=how_many)


def generate_tile(tile_size, output_file):
    img = _image_template()
    pixels = img.load()
    num_bits = tile_size * tile_size
    bits = _get_random_bits(num_bits)
    for i, b in enumerate(bits):
        x = i % tile_size
        y = i // tile_size
        if b:
            pixels[x, y] = (0, 0, 0)
    return img


def generate_tileset(seed, num_tiles=16):
    random.seed(seed)
    dir_path = _path(seed)
    try:
        mkdir(dir_path)
    except FileExistsError:
        pass

    for t in range(num_tiles):
        tile_path = path.join(dir_path, f'{t:02x}.png')
        img = generate_tile(8, tile_path)
        img.save(tile_path)


def main():
    random.seed()
    for run in range(5):
        tileset_seed = random.getrandbits(128)
        true_random = random.getstate()
        generate_tileset(tileset_seed)
        random.setstate(true_random)


if __name__ == '__main__':
    main()