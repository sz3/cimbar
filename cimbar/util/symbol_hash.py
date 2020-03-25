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

        self.dim = dim
        self.center = self._image_hash_slice(binary_array, (1, 1), (dim-1, dim-1))

        symbol_dim = dim - 2
        corners = [
            (0, 0), (symbol_dim, symbol_dim),
            (0, 2), (symbol_dim, dim),
            (2, 0), (dim, symbol_dim),
            (2, 2), (dim, dim),
        ]
        self.corners = [self._image_hash_slice(binary_array, *c) for c in corners]

    def _image_hash_slice(self, binary_array, start, end):
        res = matrix_slice(binary_array, self.dim, start, end)
        return imagehash.ImageHash(res)

    def __eq__(self, other):
        return self - other == 0  # for now...

    def __sub__(self, other):
        # compare both center to everything
        # compare corners to their corresponding corner
        mind = self.center - other.center
        for c in other.corners:
            mind = min(mind, self.center - c)
        for c in self.corners:
            mind = min(mind, other.center - c)
        for mc, oc in zip(self.corners, other.corners):
            mind = min(mind, mc - oc)
        return mind


def symhash(img, size=8):
    baseline = imagehash.average_hash(img, size)
    return SymbolicHash(baseline, size)
