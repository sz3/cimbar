
from unittest import TestCase

from cimbar.util.interleave import interleave, interleave_reverse


class InterleaveTest(TestCase):
    def test_interleave_encoding(self):
        a = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        a = a*3

        res = list(interleave(a, 10))
        self.assertEquals(res, sorted(a))

        res = list(interleave(a, 5, index=True))
        self.assertEquals(res, [
            (0, 0),
            (5, 5),
            (0, 10),
            (5, 15),
            (0, 20),
            (5, 25),
            (1, 1),
            (6, 6),
            (1, 11),
            (6, 16),
            (1, 21),
            (6, 26),
            (2, 2),
            (7, 7),
            (2, 12),
            (7, 17),
            (2, 22),
            (7, 27),
            (3, 3),
            (8, 8),
            (3, 13),
            (8, 18),
            (3, 23),
            (8, 28),
            (4, 4),
            (9, 9),
            (4, 14),
            (9, 19),
            (4, 24),
            (9, 29),
        ])

    def test_interleave_decoding(self):
        a = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        a = a*3

        lookup, block_size = interleave_reverse(a, 5)
        transformed = list(interleave(a, 5))

        b = [transformed[lookup[i]] for i, _ in enumerate(transformed)]
        self.assertEquals(a, b)
        self.assertEquals(block_size, 6)

