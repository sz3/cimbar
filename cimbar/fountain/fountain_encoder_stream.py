

def int_to_bytes(n):
    return n.to_bytes((n.bit_length() + 7) // 8, 'big')


def int_from_bytes(bites):
    return int.from_bytes(bites, 'big')


class fountain_header:
    pass


class fountain_stream:
    def __init__(self, f, chunk_size, f_size=None, mode='read'):
        if mode not in ['read', 'write']:
            raise Exception('bad bit_file mode. Try "read" or "write"')
        self.mode = mode

        self.buffer = b''
        self.chunk_size = chunk_size

        if isinstance(f, str):
            fmode = 'wb' if mode == 'write' else 'rb'
            self.f = open(f, fmode)
        else:
            self.f = f
        self._load(f_size)

    @property
    def closed(self):
        return self.f.closed

    def __enter__(self):
        self._load()
        return self

    def __exit__(self, type, value, traceback):
        if not self.f.closed:
            with self.f:  # close file
                pass

    # split this into fountain_encoder_stream and fountain_decoder_stream?
    # the if blocks aren't helping us enough?
    def _load(self, f_size=None):
        from pywirehair import encoder, decoder
        if self.mode == 'write':
            contents = self.f.read()
            self.fountain = encoder(contents, self.chunk_size)
            self.chunk_id = 0
            self.len = len(contents)
        else:
            self.fountain = decoder(f_size)

    def _header(self, chunk_id):
        return b''

    def write(self, buffer):
        if len(buffer) % self.chunk_size != 0:
            raise Exception(f'{len(buffer)} must be a multiple of {self.chunk_size}')

        # split buffer into header,chunk
        # get chunk_id from header
        self.fountain.decode(chunk_id, buffer)

    def read(self):
        bites = b''
        while len(bites) < self.chunk_size:
            bites = self.fountain.encode(self.chunk_id)
            self.chunk_id += 1
        return bites
