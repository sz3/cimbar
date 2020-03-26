import imagehash


def matrix_slice(l, dim, start, end):
    # start and end are tuples
    startX, startY = start
    endX, endY = end
    res = []
    print(f'len l is {len(l)}')
    for y in range(startY, endY):
        for x in range(startX, endX):
            i = x + (y*dim)
            print(f'{x}, {y} ({i}) = {l[i]}')
            res.append(l[i])
    return res


class SymbolicHash:
    def __init__(self, binary_array, dim=8):
        if isinstance(binary_array, imagehash.ImageHash):
            binary_array = binary_array.hash

        self.full = imagehash.ImageHash(binary_array)
        self.center = self._imagehash_slice(binary_array, (1, 1), (dim-1, dim-1))

        corners = [
            [(0, 0), (dim-2, dim-2)],
            [(0, 1), (dim-2, dim-1)],
            [(0, 2), (dim-2, dim)],
            [(1, 0), (dim-1, dim-2)],
            [(1, 1), (dim-1, dim-1)],
            [(1, 2), (dim-1, dim)],
            [(2, 0), (dim, dim-2)],
            [(2, 1), (dim, dim-1)],
            [(2, 2), (dim, dim)],
        ]
        self.corners = [self._imagehash_slice(binary_array, *c) for c in corners]

    def _imagehash_slice(self, binary_array, start, end):
        startX, startY = start
        endX, endY = end
        res = binary_array[startX:endX, startY:endY]
        return imagehash.ImageHash(res)

    def __hash__(self):
        return hash(self.full)

    def __eq__(self, other):
        return self - other == 0  # for now...

    def __sub__(self, other):
        # compare both centers to everything
        # compare both full
        mind = self.full - other.full
        mind = min(mind, self.center - other.center)
        for c in other.corners:
            mind = min(mind, self.center - c)
        for c in self.corners:
            mind = min(mind, other.center - c)
        return mind


def symhash(img, size=8):
    baseline = imagehash.average_hash(img, size)
    return SymbolicHash(baseline, size)
