from reedsolo import RSCodec


class reed_solomon_stream:
    def __init__(self, f, ec, block_size, mode='read', on_failure=None):
        if mode not in ['read', 'write']:
            raise Exception('bad bit_file mode. Try "read" or "write"')
        self.mode = mode
        self.rsc = RSCodec(ec, nsize=block_size, fcr=1, prim=0x187)
        self.block_size = block_size
        self.empty_block = b'\0' * (block_size-ec) if on_failure is None else on_failure

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
        i = 0
        while i < len(buffer):
            bu = buffer[i:i+self.block_size]
            try:
                decoded = bytes(self.rsc.decode(bu)[0])
                self.f.write(decoded)
            except:
                print(f'failed decode at {i}')
                self.f.write(self.empty_block)
            i += self.block_size

    def read(self, max_bytes):
        raw = self.f.read(max_bytes)
        return self.rsc.encode(raw)
