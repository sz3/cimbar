import sys
import cv2
import numpy



class ScanState:
    def __init__(self):
        self.state = 0
        self.tally = [0]

    def pop_state(self):
        # when state == 6, we need to drop down to state == 4
        self.state -= 2
        self.tally = self.tally[2:]

    def evaluate_state(self):
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
            if ratio < 2.5 or ratio > 3.5:
                return None
        anchor_width = sum(ones) + center
        return anchor_width

    def process(self, black):
        # transitions first
        is_transition = (self.state in [0, 2, 4] and black) or (self.state in [1, 3, 5] and not black)
        if is_transition:
            self.state += 1
            self.tally.append(0)
            self.tally[-1] += 1

            if self.state == 6:
                res = self.evaluate_state()
                self.pop_state()
                return res
            return None

        if self.state in [1, 3, 5] and black:
            self.tally[-1] += 1
        if self.state in [2, 4] and not black:
            self.tally[-1] += 1
        return None


class CimbarScanner:
    def __init__(self, img, skip=17):
        '''
        image dimensions need to not be divisible by skip
        '''
        self.img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, self.img = cv2.threshold(self.img, 127, 255, cv2.THRESH_BINARY)
        self.height, self.width = self.img.shape
        self.skip = skip

    def horizontal_scan(self, y):
        # print('horizontal scan at {}'.format(y))
        # for each column, look for the 1:1:3:1:1 pattern
        state = ScanState()
        for x in range(self.width):
            black = self.img[x, y] < 127
            res = state.process(black)
            if res:
                #print('found possible anchor at {}-{},{}'.format(x - res, x, y))
                yield (x-(res//2), y)

    def vertical_scan(self, x):
        state = ScanState()
        for y in range(self.width):
            black = self.img[x, y] < 127
            res = state.process(black)
            if res:
                #print('found possible anchor at {},{}-{}'.format(x, y-res, y))
                yield (x, y-(res//2))

    def diagonal_scan(self, x, y):
        # find top/left point first, then go down right
        offset = abs(x - y)
        if x < y:
            start_y = offset
            start_x = 0
        else:
            start_x = offset
            start_y = 0

        state = ScanState()
        for i in range(self.width - offset):
            x = start_x + i
            y = start_y + i
            black = self.img[x, y] < 127
            res = state.process(black)
            if res:
                print('confirmed anchor at {}-{},{}-{}'.format(x-res, x, y-res, y))
                yield (x-(res//2), y-(res//2))

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
        return results

    def t2_scan_vertical(self, candidates):
        '''
        gets a smart answer for Ys
        '''
        results = []
        xs = set([x for x, y in candidates])
        for x in xs:
            results += list(self.vertical_scan(x))
        return results

    def t3_scan_diagonal(self, candidates):
        '''
        confirm tokens
        '''
        results = []
        for x, y in candidates:
            results += list(self.diagonal_scan(x, y))
        return results

    def deduplicate_candidates(self, candidates):
        # group
        group = []
        for x, y in candidates:
            done = False
            for i, elem in enumerate(group):
                repX = elem[0][0]
                repY = elem[0][1]
                if abs(x - repX) < 10 and abs(y - repY) < 10:
                    group[i].append((x,y))
                    done = True
                    continue
            if not done:
                group.append([(x, y)])

        # average
        average = []
        for c in group:
            sumX = sumY = 0
            for x, y in c:
                sumX += x
                sumY += y
            x = sumX // len(c)
            y = sumY // len(c)
            average.append((x, y))
        return average

    def scan(self):
        # these need to be ranges, not just points
        candidates = self.t1_scan_horizontal()
        t2_candidates = self.t2_scan_vertical(candidates)
        # if duplicate candidates (e.g. within 10px or so), deduplicate
        t3_candidates = self.t3_scan_diagonal(t2_candidates)
        print(candidates)
        print(t2_candidates)
        print(t3_candidates)
        print(self.deduplicate_candidates(t3_candidates))
        return t3_candidates


def detector(img):
    cs = CimbarScanner(img, 17)
    cs.scan()
    return 'ok'


def deskewer(src_image):
    img = cv2.imread(src_image)
    res = detector(img)
    print(res)
    '''
    if not res[0]:
        print('didnt detect anything! :|')
        return
    # all corners should be 5px from image border
    # i.e. width is CELL_DIMENSIONS * CELL_SPACING - 10px
    top_left = tuple(map(tuple, res[1][0]))[0]
    bottom_left = tuple(map(tuple, res[1][1]))[0]
    bottom_right = tuple(map(tuple, res[1][2]))[0]  # speculative
    top_right = tuple(map(tuple, res[1][3]))[0]
    '''

    # print(f'top left: {top_left}, top right: {top_right}, bottom right: {bottom_right}, bottom left: {bottom_left}')

    '''size = 1024
    input_pts = numpy.float32([top_left, top_right, bottom_right, bottom_left])
    output_pts = numpy.float32([[5, 5], [5, size-5], [size-5, size-5], [size-5, 5]])
    transformer = cv2.getPerspectiveTransform(input_pts, output_pts)
    correct_prespective = cv2.warpPerspective(img, transformer, (size, size))
    cv2.imwrite('/tmp/test.png', correct_prespective)'''


def main():
    src_image = sys.argv[1]
    deskewer(src_image)


if __name__ == '__main__':
    main()