from reedsolo import RSCodec


class reed_solomon_stream:
    def __init__(self, f, ec=12, mode='read'):
        if mode not in ['read', 'write']:
            raise Exception('bad bit_file mode. Try "read" or "write"')
        self.mode = mode
        self.rsc = RSCodec(ec)

        if isinstance(f, str):
            fmode = 'wb' if mode == 'write' else 'rb'
            self.f = open(f, fmode)
        else:
            self.f = f

    @property
    def closed(self):
        return self.f.closed

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if not self.f.closed:
            with self.f:  # close file
                pass

    def write(self, buffer):
        # we can only decode multiples of 255 -- the remainder will have to be dropped
        remainder = len(buffer) % 255
        decoded = bytes(self.rsc.decode(buffer[:-remainder])[0])
        self.f.write(decoded)

    def read(self, max_bytes):
        raw = self.f.read(max_bytes)
        return self.rsc.encode(raw)
