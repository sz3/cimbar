from heapq import heappush, heappop


class cell_drift:
    pairs = [(0, 0), (1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]
    limit = 2

    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

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

    def __str__(self):
        return f'{self.x},{self.y}'


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


class AdjacentCellFinder:
    def __init__(self, cell_pos, dimensions, marker_size=6):
        self.cell_pos = cell_pos
        self.edge_offset = marker_size
        self.dimensions = dimensions

        mid_dimensions = dimensions - marker_size - marker_size
        mid_cells = dimensions * mid_dimensions
        edge_cells = mid_dimensions * marker_size
        self.first_mid = edge_cells
        self.first_bottom = edge_cells + mid_cells

    def _section(self, index):
        if index < self.first_mid:
            return 0
        elif index < self.first_bottom:
            return 1
        else:
            return 2

    def _right(self, index):
        r = index+1
        if r >= len(self.cell_pos):
            return None
        if self.cell_pos[r][0] < self.cell_pos[index][0]:  # looped
            return None
        if self.cell_pos[r][1] != self.cell_pos[index][1]:  # sanity
            return None
        return r

    def _left(self, index):
        l = index-1
        if l < 0:
            return None
        if self.cell_pos[l][0] > self.cell_pos[index][0]:  # looped
            return None
        if self.cell_pos[l][1] != self.cell_pos[index][1]:  # sanity
            return None
        return l

    def _bottom(self, index):
        # adjust for empty cells due to the marker margin
        increment = self.dimensions
        if self._section(index) in [0, 2]:
            increment -= self.edge_offset
        b = index + increment
        if self._section(b) in [0, 2]:
            b -= self.edge_offset

        if b >= len(self.cell_pos):
            return None
        if self.cell_pos[b][0] != self.cell_pos[index][0]:  # sanity
            return None
        return b

    def _top(self, index):
        # adjust for empty cells due to the marker margin
        decrement = self.dimensions
        if self._section(index) in [0, 2]:
            decrement -= self.edge_offset
        t = index - decrement
        if self._section(t) in [0, 2]:
            t += self.edge_offset

        if t < 0:
            return None
        if self.cell_pos[t][0] != self.cell_pos[index][0]:  # sanity
            return None
        return t

    def find_adjacent(self, index):
        adjs = [
            self._right(index),
            self._left(index),
            self._bottom(index),
            self._top(index),
        ]
        return [a for a in adjs if a is not None]



class LinearDecodeOrder:
    def __init__(self, positions):
        self.positions = positions
        self.drift = cell_drift()

    def __iter__(self):
        self.it = enumerate(iter(self.positions))
        return self

    def __next__(self):
        try:
            n = next(self.it)
            # index, position, drift
            return n[0], n[1], self.drift
        except StopIteration:
            raise

    def update(self, dx, dy, error_distance):
        self.drift.update(dx, dy)


class CellDecodeInstructions:
    def __init__(self, index, drift, error_distance):
        self.index = index
        self.drift = drift
        self.error_distance = error_distance

    def __lt__(self, other):
        return self.error_distance < other.error_distance


class FloodDecodeOrder:
    def __init__(self, positions, cell_finder):
        self.positions = positions
        self.cell_finder = cell_finder

    def __iter__(self):
        self.remaining = {i: coords for i, coords in enumerate(self.positions)}
        self.heap = []
        self.most_recent = 0
        # seed corners
        heappush(self.heap, CellDecodeInstructions(0, cell_drift(), 0))
        return self

    def __next__(self):
        try:
            instr = heappop(self.heap)
            while not self.remaining.pop(instr.index, None):
                instr = heappop(self.heap)
            self.most_recent = instr.index
            # index, position, drift
            # print(f'{instr.index} at prio {instr.error_distance} and drift {instr.drift}')
            return instr.index, self.positions[instr.index], instr.drift
        except IndexError:
            raise StopIteration()

    def update(self, dx, dy, error_distance):
        adjacents = self.cell_finder.find_adjacent(self.most_recent)
        for i in adjacents:
            if i in self.remaining:
                heappush(self.heap, CellDecodeInstructions(i, cell_drift(dx, dy), error_distance))

