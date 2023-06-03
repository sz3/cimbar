import sys


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
    FOUNTAIN_BLOCKS = 10

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
    ECC = 40
    ECC_BLOCK_SIZE = 216
    INTERLEAVE_PARTITIONS = 2
    FOUNTAIN_BLOCKS = 10

    CELL_DIM_Y = CELL_DIM_X
    CELL_SPACING_Y = CELL_SPACING_X
    INTERLEAVE_BLOCKS = ECC_BLOCK_SIZE
    MARKER_SIZE_X = round(54 / CELL_SPACING_X)
    MARKER_SIZE_Y = round(54 / CELL_SPACING_Y)  # 6 or 9, probably


class sq5x6:
    TOTAL_SIZE = 1006
    BITS_PER_SYMBOL = 2
    BITS_PER_COLOR = 2
    CELL_SIZE = 5
    CELL_SPACING_X = CELL_SIZE
    CELL_SPACING_Y = CELL_SIZE + 1
    CELL_DIM_Y = 165
    CELL_DIM_X = 198
    CELLS_OFFSET = 9
    ECC = 33
    ECC_BLOCK_SIZE = 163
    INTERLEAVE_PARTITIONS = 3
    FOUNTAIN_BLOCKS = 9

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
