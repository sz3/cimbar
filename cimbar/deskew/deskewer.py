import cv2
import numpy

from cimbar.deskew.scanner import CimbarScanner


def deskewer(src_image, dst_image, dark, use_edges=True, anchor_size=30):
    img = cv2.imread(src_image)
    cs = CimbarScanner(img, dark, 17)
    res = cs.scan()
    print(res.four_corners)

    if len(res.four_corners) < 4:
        print('didnt detect enough points! :(')
        return

    ''' given a 1024x1024 image and a 52px anchor size, corners should correspond to:
     (26, 26)
     (998, 26)
     (26, 998)
     (998, 998)
    '''
    # i.e. width is CELL_DIMENSIONS * CELL_SPACING
    top_left, top_right, bottom_left, bottom_right = res.four_corners
    # print(f'top left: {top_left}, top right: {top_right}, bottom right: {bottom_right}, bottom left: {bottom_left}')

    from cimbar.cimbar import TOTAL_SIZE
    size = TOTAL_SIZE

    input_pts = [top_left, top_right, bottom_right, bottom_left]
    output_pts = [
        (anchor_size, anchor_size), (size-anchor_size, anchor_size),
        (size-anchor_size, size-anchor_size), (anchor_size, size-anchor_size)
    ]
    if use_edges:
        edges = cs.scan_edges(res, anchor_size)
        print(f'edges are: {edges}')
        mid = size // 2
        for p, outP in zip(edges, [(mid, 4), (size-4, mid), (mid, size-4), (4, mid)]):
            if p:
                input_pts.append(p)
                output_pts.append(outP)

    transformer, _ = cv2.findHomography(numpy.float32(input_pts), numpy.float32(output_pts))
    correct_prespective = cv2.warpPerspective(img, transformer, (size, size))
    cv2.imwrite(dst_image, correct_prespective)
