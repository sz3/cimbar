from .header import fountain_header

class fountain_decoder_stream:
    def __init__(self, f, chunk_size):
        self.write_size = chunk_size
        self.chunk_size = chunk_size - fountain_header.length
        if isinstance(f, str):
            self.f = open(f, 'wb')
        else:
            self.f = f
        self.fountain = None
        self.buffer = b''
        self.done = False
        self.headers = []

    @property
    def closed(self):
        return self.f.closed

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if not self.f.closed:
            with self.f:
                pass

    def _reset(self, total_size):
        from pywirehair import decoder
        self.fountain = decoder(total_size, self.chunk_size)

    def write(self, buffer):
        if self.done:
            return True

        self.buffer += buffer
        if len(self.buffer) < self.write_size:
            return False

        buffer = self.buffer[0:self.write_size]
        self.buffer = self.buffer[self.write_size:]

        # split buffer into header,chunk
        # get chunk_id and total_size from header
        hdr = fountain_header(buffer[0:fountain_header.length])

        self.headers.append(buffer[0:fountain_header.length])
        # sanity check/fail if hdr is bad? Will be all 0s if decode failed...
        if hdr.encode_id == 0 and hdr.total_size == 0 and hdr.chunk_id == 0:
            print('failed fountain decode! ...move along')
            return False

        if not self.fountain:
            self._reset(hdr.total_size)

        res = self.fountain.decode(hdr.chunk_id, buffer[fountain_header.length:])
        if not res:
            return False

        self.f.write(res)
        self.done = True
        return True
