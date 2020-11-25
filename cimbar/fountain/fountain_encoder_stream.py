from .header import fountain_header


class fountain_encoder_stream:
    def __init__(self, f, chunk_size, encode_id=0):
        self.buffer = b''
        self.chunk_size = chunk_size - fountain_header.length
        self.encode_id = encode_id

        if isinstance(f, str):
            self.f = open(f, 'rb')
        else:
            self.f = f
        self._reset()

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

    def _reset(self):
        from pywirehair import encoder
        contents = self.f.read()
        self.fountain = encoder(contents, self.chunk_size)
        self.chunk_id = 0
        self.len = len(contents)

    def _header(self, chunk_id):
        return bytes(fountain_header(self.encode_id, self.len, chunk_id))

    def read(self):
        bites = b''
        while len(bites) < self.chunk_size:
            bites = self.fountain.encode(self.chunk_id)
            self.chunk_id += 1
        return self._header(self.chunk_id - 1) + bites
