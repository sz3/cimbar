import bitstring
from bitstring import Bits, BitStream


MAX_ENCODING = 16384


class bit_file:
    def __init__(self, f, bits_per_op, mode='read', read_size=MAX_ENCODING):
        if mode not in ['read', 'write']:
            raise Exception('bad bit_file mode. Try "read" or "write"')
        self.mode = mode

        if isinstance(f, str):
            fmode = 'wb' if mode == 'write' else 'rb'
            self.f = open(f, fmode)
        else:
            self.f = f
        self.bits_per_op = bits_per_op
        self.stream = BitStream()
        if mode == 'read':
            self.stream.append(Bits(bytes=self.f.read(read_size)))

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self.mode == 'write':
            self.save()
        if not self.f.closed:
            with self.f:  # close file
                pass

    def write(self, bits):
        b1 = Bits(uint=bits, length=self.bits_per_op)
        self.stream.append(b1)

    def read(self):
        try:
            bits = self.stream.read(f'uint:{self.bits_per_op}')
        except bitstring.ReadError:
            try:
                bits = self.stream.read('uint')
            except bitstring.InterpretError:
                bits = 0
        return bits

    def save(self):
        self.f.write(self.stream.tobytes())
