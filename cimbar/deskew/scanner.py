import cv2
import numpy

from cimbar.util.geometry import calculate_midpoints


def next_power_of_two_plus_one(x):
    return 2**((x - 1).bit_length()) + 1


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

    @property
    def max_range(self):
        return max(abs(self.x - self.xmax), abs(self.y - self.ymax))

    @property
    def size(self):
        return (self.x - self.xmax)**2 + (self.y - self.ymax)**2

    def is_mergeable(self, rhs, cutoff):
        if abs(self.xavg - rhs.xavg) > cutoff or abs(self.yavg - rhs.yavg) > cutoff:
            return False

        ratio = rhs.max_range * 10 / self.max_range
        return ratio > 6 and ratio < 17

    def __repr__(self):
        return f'({self.xavg}+-{self.xrange}, {self.yavg}+-{self.yrange})'

    def __lt__(self, rhs):
        # distance from top left corner
        return self.xavg + self.yavg < rhs.xavg + rhs.yavg


class ScanState:
    RATIO_LIMITS = {
        '1:1:4': [(3.0, 6.0), (3.0, 6.0)],
        '1:2:2': [(1.0, 3.0), (0.5, 1.5)],
    }

    def __init__(self, ratio='1:1:4'):
        self.state = 0
        self.tally = [0]
        self.limits = self.RATIO_LIMITS[ratio]

    def pop_state(self):
        # when state == 6, we need to drop down to state == 4
        self.state -= 2
        self.tally = self.tally[2:]

    def evaluate_state(self):
        if self.state != 6:
            return None
        # ratio should be 1:1:4:1:1
        ones = self.tally[1:6]
        for s in ones:
            if not s:
                return None

        center = ones.pop(2)
        instructions = {
            ones[0]: self.limits[0],
            ones[1]: self.limits[1],
            ones[2]: self.limits[1],
            ones[3]: self.limits[0],
        }
        for s, limits in instructions.items():
            ratio_min = center / (s + 1)
            ratio_max = center / max(1, s - 1)
            if ratio_max < limits[0] or ratio_min > limits[1]:
                return None
        anchor_width = sum(ones) + center
        return anchor_width

    def process(self, active):
        # transitions first
        is_transition = (self.state in [0, 2, 4] and active) or (self.state in [1, 3, 5] and not active)
        if is_transition:
            self.state += 1
            self.tally.append(0)
            self.tally[-1] += 1

            if self.state == 6:
                res = self.evaluate_state()
                self.pop_state()
                return res
            return None

        # not is_transition
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
    x = int(min(img.shape[0], img.shape[1]) * 0.002)
    blur_unit = next_power_of_two_plus_one(x)
    blur_unit = max(3, blur_unit)  # needs to be at least 3
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = cv2.GaussianBlur(img,(blur_unit,blur_unit),0)

    x = int(min(img.shape[0], img.shape[1]) * 0.05)
    thresh_unit = next_power_of_two_plus_one(x)
    #img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, thresh_unit, 0)

    ret3,img = cv2.threshold(img,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
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
        self.skip = skip or self.height // 200
        self.cutoff = self.height // 30
        self.scan_ratio = '1:1:4'

    def _test_pixel(self, x, y):
        if self.dark:
            return self.img[y, x] > 127
        else:
            return self.img[y, x] < 127

    def horizontal_scan(self, y, r=None):
        # for each column, look for the 1:1:4:1:1 pattern
        if r:
            r = (max(r[0], 0), min(r[1], self.width))
        else:
            r = (0, self.width)

        state = ScanState(self.scan_ratio)
        for x in range(*r):
            active = self._test_pixel(x, y)
            res = state.process(active)
            if res:
                #print('found possible anchor at {}-{},{}'.format(x - res, x, y))
                yield Anchor(x=x-res, xmax=x-1, y=y)

        # if the pattern is at the edge of the range
        res = state.process(False)
        if res:
            x = r[1]
            yield Anchor(x=x-res, xmax=x-1, y=y)

    def vertical_scan(self, x, xmax=None, r=None):
        xmax = xmax or x
        xavg = (x + xmax) // 2
        if r:
            r = (max(r[0], 0), min(r[1], self.height))
            # print(f'vertically scanning {xavg} from {r} instead of all the way to {self.height}')
        else:
            r = (0, self.height)

        state = ScanState(self.scan_ratio)
        for y in range(*r):
            active = self._test_pixel(xavg, y)
            res = state.process(active)
            if res:
                #print('found possible anchor at {},{}-{}'.format(xavg, y-res, y))
                yield Anchor(x=x, xmax=xmax, y=y-res, ymax=y-1)

         # if the pattern is at the edge of the range
        res = state.process(False)
        if res:
            y = r[1]
            yield Anchor(x=x, xmax=xmax, y=y-res, ymax=y-1)

    def diagonal_scan(self, start_x, end_x, start_y, end_y):
        end_x = min(self.width, end_x)
        end_y = min(self.height, end_y)

        # if we're up against the top/left bounds, roll the scan forward until we're inside the bounds
        if start_x < 0:
            offset = -start_x
            start_x += offset
            start_y += offset
        if start_y < 0:
            offset = -start_y
            start_x += offset
            start_y += offset

        #print(f'diagonally scanning from {start_x},{start_y} to {end_x},{end_y}')

        state = ScanState(self.scan_ratio)
        x = start_x
        y = start_y
        while x < end_x and y < end_y:
            active = self._test_pixel(x, y)
            res = state.process(active)
            if res:
                ax, axmax = (x-res, x)
                ay, aymax = (y-res, y)
                yield Anchor(x=ax, xmax=axmax, y=ay, ymax=aymax)
            x += 1
            y += 1

         # if the pattern is at the edge of the image
        res = state.process(False)
        if res:
            yield Anchor(x=x-res, xmax=x, y=y-res, ymax=y)

    def t1_scan_horizontal(self, skip=None, start_y=None, end_y=None, r=None):
        '''
        gets a smart answer for Xs
        '''
        if not skip:
            skip = self.skip
        y = start_y or 0

        if not end_y:
            end_y = self.height
        else:
            end_y = min(end_y, self.height)

        results = []
        y += skip
        while y < end_y:
            results += list(self.horizontal_scan(y, r))
            y += skip
        return results

    def t2_scan_vertical(self, candidates):
        '''
        gets a smart answer for Ys
        '''
        results = []
        for p in candidates:
            range_guess = (p.y - (3 * p.xrange), p.y + (3 * p.xrange))
            results += list(self.vertical_scan(p.x, p.xmax, range_guess))
        return results

    def t3_scan_diagonal(self, candidates):
        '''
        confirm tokens
        '''
        results = []
        for p in candidates:
            range_guess = (p.xavg - (2 * p.yrange), p.xavg + (2 * p.yrange), p.y - p.yrange, p.ymax + p.yrange)
            results += list(self.diagonal_scan(*range_guess))
        return results

    def t4_confirm_scan(self, candidates, merge=True):
        def _confirm_results(p, res, cutoff):
            return [
                c for c in (res or []) if c.is_mergeable(p, cutoff)
            ]

        results = []
        for p in candidates:
            xrange = (p.x - p.xrange, p.xmax + p.xrange)
            yavg = p.yavg
            for y in [yavg - 1, yavg, yavg + 1]:
                xs = list(self.horizontal_scan(y, r=xrange))
                confirms = _confirm_results(p, xs, self.cutoff // 2)
                if not confirms:
                    p = None
                    break
                if merge:
                    for c in confirms:
                        p.merge(c)
            if not p:
                continue

            yrange = (p.y - p.yrange, p.ymax + p.yrange)
            xavg = p.xavg
            for x in [xavg - 1, xavg, xavg + 1]:
                ys = list(self.vertical_scan(x, r=yrange))
                confirms = _confirm_results(p, ys, self.cutoff // 2)
                if not confirms:
                    p = None
                    break
                if merge:
                    for c in confirms:
                        p.merge(c)
            if not p:
                continue

            results.append(p)

        return self.deduplicate_candidates(results)

    def deduplicate_candidates(self, candidates):
        # group
        group = []
        for p in candidates:
            done = False
            for i, elem in enumerate(group):
                rep = elem[0]
                if rep.is_mergeable(p, self.cutoff):
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
        return average

    def filter_candidates(self, candidates):
        if len(candidates) < 3:
            return candidates, None

        candidates.sort(key=lambda c: c.size)
        best_candidates = candidates[-3:]

        xrange = sum([c.xrange for c in best_candidates])
        yrange = sum([c.yrange for c in best_candidates])
        xrange = xrange // len(best_candidates)
        yrange = yrange // len(best_candidates)
        max_range = max(xrange, yrange)

        return ([c for c in best_candidates if c.xrange >= xrange / 2 and c.yrange >= yrange / 2], max_range)

    def sort_top_to_bottom(self, candidates):
        # calculate distance from candidates. Longest = 2,3
        # 2 = clockwise from 1
        def _fix_index(idx):
            if idx < 0:
                idx = 2
            elif idx > 2:
                idx = 0
            return idx

        print(f'sorting {candidates} in tl-tr-bl order.')

        # get edges
        cs = [
            (p.xavg, p.yavg) for p in candidates
        ]
        edges = [
            numpy.subtract(cs[1], cs[2]),
            numpy.subtract(cs[2], cs[0]),
            numpy.subtract(cs[0], cs[1]),
        ]

        # find longest edge. This will correspond to the index of the anchor opposite it (thanks to our ordering of `edges`)
        top_left = 0
        max_d = 0
        for i, e in enumerate(edges):
            dist = e.dot(e)
            if dist > max_d:
                max_d = dist
                top_left = i

        # compare the directions of the incoming/departing edges to figure out which way is clockwise
        departing_edge = edges[_fix_index(top_left - 1)]
        incoming_edge = edges[_fix_index(top_left + 1)]
        incoming_edge = (-incoming_edge[1], incoming_edge[0])  # rotate 90 degrees right
        overlap = departing_edge - incoming_edge

        if overlap.dot(overlap) < departing_edge.dot(departing_edge):
            top_right = _fix_index(top_left + 1)
            bottom_left = _fix_index(top_left - 1)
        else:
            top_right = _fix_index(top_left - 1)
            bottom_left = _fix_index(top_left + 1)

        candidates = [
            candidates[top_left],
            candidates[top_right],
            candidates[bottom_left],
        ]
        return candidates

    def scan(self):
        self.scan_ratio = '1:1:4'
        candidates = self.t1_scan_horizontal()
        t2_candidates = self.t2_scan_vertical(candidates)
        # if duplicate candidates (e.g. within 10px or so), deduplicate
        t3_candidates = self.t3_scan_diagonal(t2_candidates)
        t4_candidates = self.t4_confirm_scan(t3_candidates)
        print(candidates)
        print(t2_candidates)
        print(t3_candidates)
        print(t4_candidates)

        filtered_candidates, max_range = self.filter_candidates(t4_candidates)
        print(f'filtered: {filtered_candidates}')

        candidates = self.sort_top_to_bottom(filtered_candidates)
        corners = self.add_fourth_corner(candidates, max_range)
        return CimbarAlignment(corners)

    def add_fourth_corner(self, candidates, max_range):
        anchors = [(p.xavg, p.yavg) for p in candidates]
        self.scan_ratio = '1:2:2'

        top_scalar = candidates[2].max_range / max(candidates[1].max_range, candidates[0].max_range)
        top_edge = numpy.subtract(anchors[1], anchors[0]) * top_scalar
        left_scalar = candidates[1].max_range / max(candidates[2].max_range, candidates[0].max_range)
        left_edge = numpy.subtract(anchors[2], anchors[0]) * left_scalar

        bottom_right_guess1 = anchors[2] + top_edge
        bottom_right_guess2 = anchors[1] + left_edge
        bottom_right_speculative = (bottom_right_guess1 + bottom_right_guess2) // 2
        print(f'bottom right guess: {bottom_right_speculative}')

        fourth = self.scan_fourth_corner(bottom_right_speculative, max_range, max_range)
        if fourth:
            anchors.append(fourth)
        return anchors

    def scan_fourth_corner(self, center, xrange, yrange):
        uncertainty = 4
        start_y = int(center[1] - (yrange * uncertainty))
        end_y = int(center[1] + (yrange * uncertainty))
        start_x = int(center[0] - (xrange * uncertainty))
        end_x = int(center[0] + (xrange * uncertainty))

        skip = self.skip // 2
        print(f'looking for 4th corner at {start_x}-{end_x},{start_y}-{end_y}. skip={skip}')

        candidates = self.t1_scan_horizontal(skip=skip, start_y=start_y, end_y=end_y, r=(start_x, end_x))
        print('4 candidates: {}'.format(candidates))
        t2_candidates = self.t2_scan_vertical(candidates)
        print('4 t2 candidates: {}'.format(t2_candidates))
        candidates = [c for c in t2_candidates if c.xrange >= xrange / 2 and c.yrange >= yrange / 2]
        if not candidates:
            return None

        t3_candidates = self.t3_scan_diagonal(t2_candidates)
        print('4 t3 candidates: {}'.format(t3_candidates))
        t4_candidates = self.t4_confirm_scan(t3_candidates, merge=False)
        t4_candidates.sort(key=lambda c: c.size)


        print('4 t4 candidates: {}'.format(t4_candidates))
        c4 = t4_candidates[-1]
        if c4.xrange < (xrange / 2) or c4.yrange < (yrange / 2):
            return None
        return (c4.xavg, c4.yavg)

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
        #print(f'edge {u} -> {v}, distance {distance_v}')

        mid_point = mid_point or numpy.add(u, distance_v / 2)
        mid_point_anchor_adjust = numpy.multiply(out_v, anchor_size / 16)
        mid_point += mid_point_anchor_adjust

        in_v = (-out_v[0], -out_v[1])
        for check in (out_v, in_v):
            max_check = max(abs(check[0]), abs(check[1]))
            unit = check / max_check

            state = EdgeScanState()
            i, j = 0, 0
            while abs(i) <= abs(check[0]) and abs(j) <= abs(check[1]):
                x = int(mid_point[0] + i)
                y = int(mid_point[1] + j)
                if x < 0 or x >= self.width or y < 0 or y >= self.height:
                    i += unit[0]
                    j += unit[1]
                    continue
                active = self._test_pixel(x, y)
                size = state.process(active)
                if size:
                    #print(f' found edge at {x}, {y}. {i}, {j}. {size}')
                    edge = numpy.subtract((x, y), (unit*size)/2).astype(int)
                    if self.chase_edge(edge, distance_unit):
                        return edge[0], edge[1]
                i += unit[0]
                j += unit[1]
        #print(' ... no edge?!?!?')
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
