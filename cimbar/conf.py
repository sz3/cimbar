import sys


class sq8x8og:
    TOTAL_SIZE = 1024
    BITS_PER_SYMBOL = 4
    BITS_PER_COLOR = 2
    CELL_SIZE = 8
    CELL_SPACING_X = CELL_SIZE + 1
    CELL_DIM_X = 112
    CELLS_OFFSET = 8
    ECC = 30
    ECC_BLOCK_SIZE = 155
    INTERLEAVE_PARTITIONS = 2
    FOUNTAIN_BLOCKS = 10

    CELL_DIM_Y = CELL_DIM_X
    CELL_SPACING_Y = CELL_SPACING_X
    INTERLEAVE_BLOCKS = ECC_BLOCK_SIZE
    MARKER_SIZE_X = round(54 / CELL_SPACING_X)
    MARKER_SIZE_Y = round(54 / CELL_SPACING_Y)  # 6 or 9, probably


class sq8x8:
    TOTAL_SIZE = 1024
    BITS_PER_SYMBOL = 4
    BITS_PER_COLOR = 2
    CELL_SIZE = 8
    CELL_SPACING_X = CELL_SIZE + 1
    CELL_DIM_X = 112
    CELLS_OFFSET = 8
    ECC = 30
    ECC_BLOCK_SIZE = 155
    INTERLEAVE_PARTITIONS = 2
    FOUNTAIN_BLOCKS = 0  # dynamic

    CELL_DIM_Y = CELL_DIM_X
    CELL_SPACING_Y = CELL_SPACING_X
    INTERLEAVE_BLOCKS = ECC_BLOCK_SIZE
    MARKER_SIZE_X = round(54 / CELL_SPACING_X)
    MARKER_SIZE_Y = round(54 / CELL_SPACING_Y)  # 6 or 9, probably


class sq5x5:
    TOTAL_SIZE = 988
    BITS_PER_SYMBOL = 2
    BITS_PER_COLOR = 2
    CELL_SIZE = 5
    CELL_SPACING_X = CELL_SIZE + 1
    CELL_DIM_X = 162
    CELLS_OFFSET = 9
    ECC = 40  # 32?
    ECC_BLOCK_SIZE = 216  # 162?
    INTERLEAVE_PARTITIONS = 2
    FOUNTAIN_BLOCKS = 0  # dynamic

    CELL_DIM_Y = CELL_DIM_X
    CELL_SPACING_Y = CELL_SPACING_X
    INTERLEAVE_BLOCKS = ECC_BLOCK_SIZE
    MARKER_SIZE_X = round(54 / CELL_SPACING_X)
    MARKER_SIZE_Y = round(54 / CELL_SPACING_Y)  # 6 or 9, probably


class sq5x6:
    TOTAL_SIZE = 966
    BITS_PER_SYMBOL = 2
    BITS_PER_COLOR = 2
    CELL_SIZE = 5
    CELL_SPACING_X = CELL_SIZE
    CELL_SPACING_Y = CELL_SIZE + 1
    CELL_DIM_Y = 158
    CELL_DIM_X = 190
    CELLS_OFFSET = 9
    ECC = 31
    ECC_BLOCK_SIZE = 161
    INTERLEAVE_PARTITIONS = 23  # or just leave ecc locked, and do 2,10?
    FOUNTAIN_BLOCKS = 23

    INTERLEAVE_BLOCKS = ECC_BLOCK_SIZE
    MARKER_SIZE_X = round(54 / CELL_SPACING_X)
    MARKER_SIZE_Y = round(54 / CELL_SPACING_Y)  # 6 or 9, probably


# this one is very flexible, probably good for experimenting with
class sq5x6alt:
    TOTAL_SIZE = 958
    BITS_PER_SYMBOL = 2
    BITS_PER_COLOR = 2
    CELL_SIZE = 5
    CELL_SPACING_X = CELL_SIZE
    CELL_SPACING_Y = CELL_SIZE + 1
    CELL_DIM_Y = 157
    CELL_DIM_X = 188
    CELLS_OFFSET = 9
    ECC = 35
    ECC_BLOCK_SIZE = 182
    INTERLEAVE_PARTITIONS = 2
    FOUNTAIN_BLOCKS = 0  # dynamic

    INTERLEAVE_BLOCKS = ECC_BLOCK_SIZE
    MARKER_SIZE_X = round(54 / CELL_SPACING_X)
    MARKER_SIZE_Y = round(54 / CELL_SPACING_Y)  # 6 or 9, probably


# swing for the fences
class sq5x6beeg:
    TOTAL_SIZE = 1051
    BITS_PER_SYMBOL = 2
    BITS_PER_COLOR = 2
    CELL_SIZE = 5
    CELL_SPACING_X = CELL_SIZE
    CELL_SPACING_Y = CELL_SIZE + 1
    CELL_DIM_Y = 172
    CELL_DIM_X = 207
    CELLS_OFFSET = 9
    ECC = 33
    ECC_BLOCK_SIZE = 163
    INTERLEAVE_PARTITIONS = 3
    FOUNTAIN_BLOCKS = 0  # dynamic

    INTERLEAVE_BLOCKS = ECC_BLOCK_SIZE
    MARKER_SIZE_X = round(54 / CELL_SPACING_X)
    MARKER_SIZE_Y = round(54 / CELL_SPACING_Y)  # 6 or 9, probably


def init(cls):
    this = sys.modules[__name__]
    this.known = {k:v for k,v in this.__dict__.items() if isinstance(v, type)}

    for k,v in cls.__dict__.items():
        if k.startswith('_'):
            continue
        setattr(this, k, v)

init(sq8x8)
