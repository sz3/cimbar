
def int_to_bytes(n, num_bytes):
    return n.to_bytes(num_bytes, 'big')


def int_from_bytes(bites):
    return int.from_bytes(bites, 'big')


class fountain_header:
    def __init__(self, encode_id, total_size=None, chunk_id=None):
        if total_size is None:
            self.encode_id, self.total_size, self.chunk_id = self.from_encoded(encode_id)
        else:
            self.encode_id = encode_id
            self.total_size = total_size
            self.chunk_id = chunk_id

    def __bytes__(self):
        return int_to_bytes(self.encode_id, 1) + int_to_bytes(self.total_size, 3) + int_to_bytes(self.chunk_id, 2)

    @classmethod
    def from_encoded(cls, encoded_bytes):
        encode_id = int_from_bytes(encoded_bytes[0:1])
        total_size = int_from_bytes(encoded_bytes[1:4])
        chunk_id = int_from_bytes(encoded_bytes[4:6])
        return encode_id, total_size, chunk_id
