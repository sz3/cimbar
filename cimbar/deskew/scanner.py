import cv2
import numpy

from cimbar.util.geometry import calculate_midpoints


# should be thought of as a line, not an area
class Anchor:
    __slots__ = 'x', 'xmax', 'y', 'ymax'

    def __init__(self, x, y, xmax=None, ymax=None):
        self.x = x
        self.y = y
        self.xmax = xmax or x
        self.ymax = ymax or y

    def merge(self, rhs):
        self.x = min(self.x, rhs.x)
        self.xmax = max(self.xmax, rhs.xmax)
        self.y = min(self.y, rhs.y)
        self.ymax = max(self.ymax, rhs.ymax)

    @property
    def xavg(self):
        return (self.x + self.xmax) // 2

    @property
    def yavg(self):
        return (self.y + self.ymax) // 2

    @property
    def xrange(self):
        return abs(self.x - self.xmax) // 2

    @property
    def yrange(self):
        return abs(self.y - self.ymax) // 2

    def __repr__(self):
        return f'({self.xavg}+-{self.xrange}, {self.yavg}+-{self.yrange})'

    def __lt__(self, rhs):
        # distance from top left corner
        return self.xavg + self.yavg < rhs.xavg + rhs.yavg


class ScanState:
    def __init__(self):
        self.state = 0
        self.tally = [0]

    def pop_state(self):
        # when state == 6, we need to drop down to state == 4
        self.state -= 2
        self.tally = self.tally[2:]

    def evaluate_state(self, leniency):
        if self.state != 6:
            return None
        # ratio should be 1:1:3:1:1
        ones = self.tally[1:6]
        for s in ones:
            if not s:
                return None
        center = ones.pop(2)
        for s in ones:
            ratio = center / s
            if ratio < leniency or ratio > 5.5:
                return None
        anchor_width = sum(ones) + center
        return anchor_width

    def process(self, active, leniency=3.0):
        # transitions first
        is_transition = (self.state in [0, 2, 4] and active) or (self.state in [1, 3, 5] and not active)
        if is_transition:
            self.state += 1
            self.tally.append(0)
            self.tally[-1] += 1

            if self.state == 6:
                res = self.evaluate_state(leniency)
                self.pop_state()
                return res
            return None

        if self.state in [1, 3, 5] and active:
            self.tally[-1] += 1
        if self.state in [2, 4] and not active:
            self.tally[-1] += 1
        return None


class EdgeScanState:
    def __init__(self):
        self.state = 0
        self.tally = [0]

    def pop_state(self):
        self.state -= 2
        self.tally = self.tally[2:]

    def process(self, active):
        is_transition = (self.state in [0] and active) or (self.state in [1] and not active)
        if is_transition:
            self.state += 1
            self.tally.append(0)
            self.tally[-1] += 1

            if self.state == 2:
                res = self.tally[1]
                self.pop_state()
                return res
            return None
        if self.state in [1] and active:
            self.tally[-1] += 1
        if self.state in [0] and not active:
            self.tally[-1] += 1
        return None


def _the_works(img):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = cv2.GaussianBlur(img,(17,17),0)
    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(100,100))
    img = clahe.apply(img)
    _, img = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
    return img


class CimbarAlignment:
    def __init__(self, corners, edges=[], midpoints=[]):
        self.corners = corners
        self.edges = edges
        self.midpoints = midpoints

    @property
    def top_left(self):
        return self.corners[0]

    @property
    def top_right(self):
        return self.corners[1]

    @property
    def bottom_left(self):
        return self.corners[2]

    @property
    def bottom_right(self):
        return self.corners[3]

    @property
    def top_mid(self):
        return self.midpoints[0]

    @property
    def right_mid(self):
        return self.midpoints[1]

    @property
    def bottom_mid(self):
        return self.midpoints[2]

    @property
    def left_mid(self):
        return self.midpoints[3]


class CimbarScanner:
    def __init__(self, img, dark=False, skip=17):
        '''
        image dimensions need to not be divisible by skip
        '''
        self.img = _the_works(img)
        self.height, self.width = self.img.shape
        self.dark = dark
        self.skip = skip

    def _test_pixel(self, x, y):
        if self.dark:
            return self.img[y, x] > 127
        else:
            return self.img[y, x] < 127

    def horizontal_scan(self, y):
        # print('horizontal scan at {}'.format(y))
        # for each column, look for the 1:1:3:1:1 pattern
        state = ScanState()
        for x in range(self.width):
            active = self._test_pixel(x, y)
            res = state.process(active)
            if res:
                #print('found possible anchor at {}-{},{}'.format(x - res, x, y))
                yield Anchor(x=x-res, xmax=x-1, y=y)

        # if the pattern is at the edge of the image
        res = state.process(False)
        if res:
            x = self.width
            yield Anchor(x=x-res, xmax=x-1, y=y)

    def vertical_scan(self, x, r=None):
        state = ScanState()
        if r:
            r = (max(r[0], 0), min(r[1], self.height))
            # print(f'vertically scanning {x} from {r} instead of all the way to {self.height}')
        else:
            r = (0, self.height)
        for y in range(*r):
            active = self._test_pixel(x, y)
            res = state.process(active)
            if res:
                #print('found possible anchor at {},{}-{}'.format(x, y-res, y))
                yield Anchor(x=x, y=y-res, ymax=y-1)

         # if the pattern is at the edge of the image
        res = state.process(False)
        if res:
            y = self.height
            yield Anchor(x=x, y=y-res, ymax=y-1)

    def diagonal_scan(self, start_x, end_x, start_y, end_y):
        start_x = max(0, start_x)
        start_y = max(0, start_y)
        end_x = min(self.width, end_x)
        end_y = min(self.height, end_y)

        # print(f'diagonally scanning from {start_x},{start_y} to {end_x},{end_y}')

        state = ScanState()
        x = start_x
        y = start_y
        while x < self.width and y < self.height:
            active = self._test_pixel(x, y)
            #if (target_x, target_y) == (346, 3005):
            #    print(f'{x},{y} == {active}')
            #if (x, y) == (394,3053):
            #    print(f'{state.tally}')
            res = state.process(active, leniency=3.0)
            if res:
                print('confirmed anchor at {}-{},{}-{}'.format(x-res, x, y-res, y))
                yield Anchor(x=x-res, xmax=x, y=y-res, ymax=y)
            x += 1
            y += 1

         # if the pattern is at the edge of the image
        res = state.process(False)
        if res:
            yield Anchor(x=x-res, xmax=x, y=y-res, ymax=y)

    def t1_scan_horizontal(self):
        '''
        gets a smart answer for Xs
        '''
        results = []
        y = 0
        y += self.skip
        while y < self.height:  # eventually != 0?
            if y > self.height:
                y = y % self.height
            results += list(self.horizontal_scan(y))
            y += self.skip
        return self.deduplicate_candidates(results)

    def t2_scan_vertical(self, candidates):
        '''
        gets a smart answer for Ys
        '''
        results = []
        for p in candidates:
            range_guess = (p.y - (2 * p.xrange), p.y + (2 * p.xrange))
            results += list(self.vertical_scan(p.xavg, range_guess))
        return self.deduplicate_candidates(results)

    def t3_scan_diagonal(self, candidates):
        '''
        confirm tokens
        '''
        results = []
        for p in candidates:
            range_guess = (p.x - (2 * p.yrange), p.x + (2 * p.yrange), p.y - p.yrange, p.ymax + p.yrange)
            results += list(self.diagonal_scan(*range_guess))
        return self.deduplicate_candidates(results)

    def deduplicate_candidates(self, candidates):
        # group
        group = []
        for p in candidates:
            done = False
            for i, elem in enumerate(group):
                rep = elem[0]
                if abs(p.xavg - rep.xavg) < 50 and abs(p.yavg - rep.yavg) < 50:
                    group[i].append(p)
                    done = True
                    continue
            if not done:
                group.append([p])

        # average
        average = []
        for c in group:
            area = c[0]
            for p in c:
                area.merge(p)
            average.append(area)
        return self.filter_candidates(average)

    def filter_candidates(self, candidates):
        if len(candidates) <= 4:
            return candidates

        candidates.sort(key=lambda c: c.xrange + c.yrange)
        best_candidates = candidates[-4:]

        xrange = sum([c.xrange for c in best_candidates])
        yrange = sum([c.yrange for c in best_candidates])
        xrange = xrange // len(best_candidates)
        yrange = yrange // len(best_candidates)

        return [c for c in candidates if c.xrange > xrange / 2 and c.yrange > yrange / 2]

    def sort_top_to_bottom(self, candidates):
        candidates.sort()
        top_left = candidates[0]
        p1 = candidates[1]
        p2 = candidates[2]
        p1_xoff = abs(p1.xavg - top_left.xavg)
        p2_xoff = abs(p2.xavg - top_left.xavg)
        if p2_xoff > p1_xoff:
            candidates = [top_left, p2, p1, candidates[3]]
        return [(p.xavg, p.yavg) for p in candidates]

    def scan(self):
        # do these need to track all known ranges, so we can approximate bounding lines?
        # also not clear if we should dedup at every step or not
        candidates = self.t1_scan_horizontal()
        t2_candidates = self.t2_scan_vertical(candidates)
        # if duplicate candidates (e.g. within 10px or so), deduplicate
        t3_candidates = self.t3_scan_diagonal(t2_candidates)
        print(candidates)
        print(t2_candidates)
        print(t3_candidates)

        return CimbarAlignment(self.sort_top_to_bottom(t3_candidates))

    def chase_edge(self, start, unit):
        # test 4 points. If we get 2/4, success
        success = 0
        for i in [-2, -1, 1, 2]:
            x = start[0] + int(unit[0] * i)
            y = start[1] + int(unit[1] * i)
            active = self._test_pixel(x, y)
            if active:
                success += 1
        return success >= 2

    def find_edge(self, u, v, mid_point, anchor_size):
        # out is always 90 degrees left?
        distance_v = numpy.subtract(v, u)
        distance_unit = distance_v / 512
        out_v = (distance_v[1] // 64, -distance_v[0] // 64)
        # print(f'edge {u} -> {v}, distance {distance_v}')

        mid_point = mid_point or numpy.add(u, distance_v / 2)
        mid_point_anchor_adjust = numpy.multiply(out_v, anchor_size / 16)
        mid_point += mid_point_anchor_adjust

        in_v = (-out_v[0], -out_v[1])
        for check in (out_v, in_v):
            max_check = max(abs(check[0]), abs(check[1]))
            unit = check / max_check

            state = EdgeScanState()
            i, j = 0, 0
            while int(i) != check[0] and int(j) != check[1]:
                x = int(mid_point[0] + i)
                y = int(mid_point[1] + j)
                active = self._test_pixel(x, y)
                size = state.process(active)
                if size:
                    # print(f'found something at {x}, {y}. {i}, {j}. {size}')
                    edge = numpy.subtract((x, y), (unit*size)/2).astype(int)
                    if self.chase_edge(edge, distance_unit):
                        return edge[0], edge[1]
                i += unit[0]
                j += unit[1]
        return None

    def scan_edges(self, align, anchor_size):
        mp = calculate_midpoints(align)
        bounds = [
            (align.top_left, align.top_right, mp.top),
            (align.top_right, align.bottom_right, mp.right),
            (align.bottom_right, align.bottom_left, mp.bottom),
            (align.bottom_left, align.top_left, mp.left),
        ]
        edges = [self.find_edge(start, end, mid, anchor_size) for start, end, mid in bounds]
        return CimbarAlignment(align.corners, edges, mp)
