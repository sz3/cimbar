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

    def _reset(self, total_size):
        from pywirehair import decoder
        self.fountain = decoder(total_size, self.chunk_size)

    def write(self, buffer):
        if len(buffer) % self.write_size != 0:
            raise Exception(f'{len(buffer)} must be a multiple of {self.write_size}')

        # split buffer into header,chunk
        # get chunk_id and total_size from header
        hdr = fountain_header(buffer[0:fountain_header.length])

        if not self.fountain:
            self._reset(hdr.total_size)

        res = self.fountain.decode(hdr.chunk_id, buffer[fountain_header.length:])
        if not res:
            return False

        self.f.write(res)
        return True
