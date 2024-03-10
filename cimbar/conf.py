import sys


class _Conf:
    # autofill the  default CELL_*_Y values somehow?
    pass


class og8x8:
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
    SPLIT_MODE=False  # legacy


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


class sq8x9bw:
    TOTAL_SIZE = (1420, 1024)
    BITS_PER_SYMBOL = 4
    BITS_PER_COLOR = 2
    CELL_SIZE = 8
    CELL_SPACING_X = CELL_SIZE + 1
    CELL_SPACING_Y = CELL_SIZE
    CELL_DIM_X = 156
    CELL_DIM_Y = 126
    CELLS_OFFSET = 9
    ECC = 34
    ECC_BLOCK_SIZE = 174
    INTERLEAVE_PARTITIONS = 2
    FOUNTAIN_BLOCKS = 0

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
    ECC = 40  # or 42?  # w/ 162, 32?
    ECC_BLOCK_SIZE = 216  # 162?
    INTERLEAVE_PARTITIONS = 2
    FOUNTAIN_BLOCKS = 0  # dynamic.. could be *2 or *3?

    CELL_DIM_Y = CELL_DIM_X
    CELL_SPACING_Y = CELL_SPACING_X
    INTERLEAVE_BLOCKS = ECC_BLOCK_SIZE
    MARKER_SIZE_X = round(54 / CELL_SPACING_X)
    MARKER_SIZE_Y = round(54 / CELL_SPACING_Y)  # 6 or 9, probably


class sq5x5wide:
    TOTAL_SIZE = (1480, 1018)
    BITS_PER_SYMBOL = 2
    BITS_PER_COLOR = 2
    CELL_SIZE = 5
    CELL_SPACING_X = CELL_SIZE + 1
    CELL_DIM_X = 244
    CELL_DIM_Y = 167
    CELLS_OFFSET = 9
    ECC = 33
    ECC_BLOCK_SIZE = 163
    INTERLEAVE_PARTITIONS = 2
    FOUNTAIN_BLOCKS = -5  # 20 (806) for 4c, 25 (806) for 8c

    CELL_SPACING_Y = CELL_SPACING_X
    INTERLEAVE_BLOCKS = ECC_BLOCK_SIZE
    MARKER_SIZE_X = round(54 / CELL_SPACING_X)
    MARKER_SIZE_Y = round(54 / CELL_SPACING_Y)  # 6 or 9, probably


class sq5x5lesswide:
    TOTAL_SIZE = (1318, 1000)
    BITS_PER_SYMBOL = 2
    BITS_PER_COLOR = 2
    CELL_SIZE = 5
    CELL_SPACING_X = CELL_SIZE + 1
    CELL_DIM_X = 217
    CELL_DIM_Y = 164
    CELLS_OFFSET = 9
    ECC = 47
    ECC_BLOCK_SIZE = 232
    INTERLEAVE_PARTITIONS = 2
    FOUNTAIN_BLOCKS = -5  # 20 (703) for 4c, 25 (703) for 8c

    CELL_SPACING_Y = CELL_SPACING_X
    INTERLEAVE_BLOCKS = ECC_BLOCK_SIZE
    MARKER_SIZE_X = round(54 / CELL_SPACING_X)
    MARKER_SIZE_Y = round(54 / CELL_SPACING_Y)  # 6 or 9, probably


class sq5x5alt:
    TOTAL_SIZE = 1024
    BITS_PER_SYMBOL = 2
    BITS_PER_COLOR = 2
    CELL_SIZE = 5
    CELL_SPACING_X = CELL_SIZE + 1
    CELL_DIM_X = 168
    CELLS_OFFSET = 9
    ECC = 30
    ECC_BLOCK_SIZE = 155
    INTERLEAVE_PARTITIONS = 3
    FOUNTAIN_BLOCKS = 9  # dynamic.. could be *2 or *3?

    CELL_DIM_Y = CELL_DIM_X
    CELL_SPACING_Y = CELL_SPACING_X
    INTERLEAVE_BLOCKS = ECC_BLOCK_SIZE
    MARKER_SIZE_X = round(54 / CELL_SPACING_X)
    MARKER_SIZE_Y = round(54 / CELL_SPACING_Y)  # 6 or 9, probably


# this one is very flexible, probably good for experimenting with
class sq5x6:
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
    FOUNTAIN_BLOCKS = -4  # dynamic ... should be *3, not *2...?

    INTERLEAVE_BLOCKS = ECC_BLOCK_SIZE
    MARKER_SIZE_X = round(54 / CELL_SPACING_X)
    MARKER_SIZE_Y = round(54 / CELL_SPACING_Y)  # 6 or 9, probably


class sq6x5:
    TOTAL_SIZE = 958
    BITS_PER_SYMBOL = 2
    BITS_PER_COLOR = 2
    CELL_SIZE = 5
    CELL_SPACING_X = CELL_SIZE + 1
    CELL_SPACING_Y = CELL_SIZE
    CELL_DIM_X = 157
    CELL_DIM_Y = 188
    CELLS_OFFSET = 9
    ECC = 35
    ECC_BLOCK_SIZE = 182
    INTERLEAVE_PARTITIONS = 2
    FOUNTAIN_BLOCKS = -4  # dynamic ... should be *3, not *2...?

    INTERLEAVE_BLOCKS = ECC_BLOCK_SIZE
    MARKER_SIZE_X = round(54 / CELL_SPACING_X)
    MARKER_SIZE_Y = round(54 / CELL_SPACING_Y)  # 6 or 9, probably


# possible bad ones that still can work with 4bit...
#... just don't try to make the numbers match for 5bit too...
# 160,192
# 165,198 (33,163,10)
class sq5x6alt:
    TOTAL_SIZE = 1026
    BITS_PER_SYMBOL = 2
    BITS_PER_COLOR = 2
    CELL_SIZE = 5
    CELL_SPACING_X = CELL_SIZE
    CELL_SPACING_Y = CELL_SIZE + 1
    CELL_DIM_Y = 168
    CELL_DIM_X = 202
    CELLS_OFFSET = 9
    ECC = 43
    ECC_BLOCK_SIZE = 215
    INTERLEAVE_PARTITIONS = 2
    FOUNTAIN_BLOCKS = 0  # dynamic ... could be *3, not *2...?

    INTERLEAVE_BLOCKS = ECC_BLOCK_SIZE
    MARKER_SIZE_X = round(54 / CELL_SPACING_X)
    MARKER_SIZE_Y = round(54 / CELL_SPACING_Y)  # 6 or 9, probably


# experimental 1.3:1 config?
class sq5x6wide:
    TOTAL_SIZE = (1306, 988)
    BITS_PER_SYMBOL = 2
    BITS_PER_COLOR = 2
    CELL_SIZE = 5
    CELL_SPACING_X = CELL_SIZE
    CELL_SPACING_Y = CELL_SIZE + 1
    CELL_DIM_Y = 162
    CELL_DIM_X = 258
    CELLS_OFFSET = 9
    ECC = 43
    ECC_BLOCK_SIZE = 207
    INTERLEAVE_PARTITIONS = 2
    FOUNTAIN_BLOCKS = 20

    INTERLEAVE_BLOCKS = ECC_BLOCK_SIZE
    MARKER_SIZE_X = round(54 / CELL_SPACING_X)
    MARKER_SIZE_Y = round(54 / CELL_SPACING_Y)  # 6 or 9, probably


class sq5x6w2:
    TOTAL_SIZE = (1286, 1012)
    BITS_PER_SYMBOL = 2
    BITS_PER_COLOR = 2
    CELL_SIZE = 5
    CELL_SPACING_X = CELL_SIZE
    CELL_SPACING_Y = CELL_SIZE + 1
    CELL_DIM_Y = 166
    CELL_DIM_X = 254
    CELLS_OFFSET = 9
    ECC = 47
    ECC_BLOCK_SIZE = 227
    INTERLEAVE_PARTITIONS = 2
    FOUNTAIN_BLOCKS = 12  # -3?

    INTERLEAVE_BLOCKS = ECC_BLOCK_SIZE
    MARKER_SIZE_X = round(54 / CELL_SPACING_X)
    MARKER_SIZE_Y = round(54 / CELL_SPACING_Y)  # 6 or 9, probably


class sq6x5wide:
    TOTAL_SIZE = (1468, 1006)
    BITS_PER_SYMBOL = 2
    BITS_PER_COLOR = 2
    CELL_SIZE = 5
    CELL_SPACING_X = CELL_SIZE + 1
    CELL_SPACING_Y = CELL_SIZE
    CELL_DIM_X = 242
    CELL_DIM_Y = 198
    CELLS_OFFSET = 9
    ECC = 33
    ECC_BLOCK_SIZE = 165
    INTERLEAVE_PARTITIONS = 2
    FOUNTAIN_BLOCKS = -6  # 24 (792) for 4color, 30??? for 8color

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

init(sq8x9bw)
