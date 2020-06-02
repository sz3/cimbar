from collections import defaultdict

from .bit_file import bit_file, bit_write_buffer


def interleave(l, num_chunks, index=False):
    num_offsets = len(l) // num_chunks
    for chunk in range(num_chunks):
        for offset in range(num_offsets):
            i = (offset * num_chunks) + chunk
            if index:
                yield l[i], i
            else:
                yield l[i]


def interleave_reverse(l, num_chunks):
    num_offsets = len(l) // num_chunks
    encoded = enumerate(interleave(l, num_chunks, index=True))
    return {lin: ilv for ilv, (_, lin) in encoded}, num_offsets


class interleaved_writer:
    def __init__(self, **kwargs):
        self.writer = bit_file(**kwargs)
        self.buffer_class = bit_write_buffer
        self.kwargs = kwargs
        self.buffers = dict()
        self.count = defaultdict(int)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.save()
        with self.writer:
            pass

    def write(self, data, block):
        self.count[block] += 1
        buff = self.buffers.get(block, None)
        if not buff:
            self.buffers[block] = buff = self.buffer_class(**self.kwargs)
        buff.write(data)

    def save(self):
        for _, buff in sorted(self.buffers.items()):
            self.writer.write(buff)
