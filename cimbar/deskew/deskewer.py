from math import sqrt

import cv2
import numpy

from cimbar import conf
from cimbar.deskew.scanner import CimbarScanner


ANCHOR_SIZE = 30
ED_DIST = 3


def correct_perspective(img, target_size, input_pts, output_pts):
    transformer = cv2.getPerspectiveTransform(numpy.float32(input_pts), numpy.float32(output_pts))
    return cv2.warpPerspective(img, transformer, target_size)


def _naive_radial_undistort(img, distortion_factor):
    '''
    This is a "works on my box" kind of function. Ideally this is a last resort (or entirely unnecessary),
    because we'll have the lens distortion parameters cached.

    distortion factor calculated by _get_distortion_factor()
    '''
    height, width = img.shape[:2]
    print('***')
    print(f'{height},{width}, ... {distortion_factor}')

    distCoeff = numpy.zeros((4,1),numpy.float64)
    distCoeff[0,0] = distortion_factor  # k1. ex: -0.0043366581750921215
    distCoeff[1,0] = 0 # k2. 0
    distCoeff[2,0] = 0.0 # tangential distortion coefficients are 0
    distCoeff[3,0] = 0.0

    cam = numpy.eye(3, dtype=numpy.float32)
    cam[0,2] = width / 2   #  center of distortion X -- assumed to be center of image
    cam[1,2] = height / 2  #  center of distortion Y
    cam[0,0] = width / 4  # "good enough" focal length
    cam[1,1] = height / 4

    return cv2.undistort(img, cam, distCoeff)


def distance(a, b):
    return sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def _edge_to_anchor_ratio(size, anchor_size):
    # target_ratio = 0.026970954356846474  # can precompute the answer if we want to
    o0 = (anchor_size, anchor_size)
    o4 = (size // 2, ED_DIST)   # 3  = edge distance
    o1 = (size-anchor_size, anchor_size)  # 994 = (size-30)
    omid = (size // 2, anchor_size)  # 512 == (size // 2)
    return distance(o4, omid) / distance(o0, o1)


def _get_distortion_factor(align, target_ratio):
    '''
    distortion_factor is generated by distance from the target_ratio.
    The expected calculation is in _edge_to_anchor_ratio()
    '''
    eparams = [
        (align.edges[0], align.top_mid, align.top_left, align.top_right),
        (align.edges[1], align.right_mid, align.top_right, align.bottom_right),
        (align.edges[2], align.bottom_mid, align.bottom_right, align.bottom_left),
        (align.edges[3], align.left_mid, align.bottom_left, align.top_left),
    ]

    all_ratios = []
    for edj, line_mid, line_start, line_end in eparams:
        if edj:
            ratio = distance(edj, line_mid) / distance(line_start, line_end)
            all_ratios.append(ratio)
    avg = sum(all_ratios) / len(all_ratios)
    return target_ratio - avg


def fix_lens_distortion(img, dest_size, anchor_size, align):
    target_ratio = _edge_to_anchor_ratio(dest_size, anchor_size)
    df = _get_distortion_factor(align, target_ratio)
    return _naive_radial_undistort(img, df)


def scan(img, dark, use_edges, size, anchor_size):
    cs = CimbarScanner(img, dark)
    align = cs.scan()
    if len(align.corners) < 4:
        return None
    if use_edges:
        align = cs.scan_edges(align, anchor_size)
    return align


def deskewer(src_image, dst_image, dark, use_edges=True, auto_dewarp=True, anchor_size=ANCHOR_SIZE):
    size = conf.TOTAL_SIZE

    img = cv2.imread(src_image)
    align = scan(img, dark, use_edges, size, anchor_size)
    if not align:
        print('didnt detect enough points! :(')
        return None

    if use_edges and auto_dewarp:
        img = fix_lens_distortion(img, size, anchor_size, align)
        # need to recalculate alignment after dewarp :(
        align = scan(img, dark, use_edges, size, anchor_size)

    input_pts = [align.top_left, align.top_right, align.bottom_right, align.bottom_left]
    output_pts = [
        (anchor_size, anchor_size), (size-anchor_size, anchor_size),
        (size-anchor_size, size-anchor_size), (anchor_size, size-anchor_size)
    ]

    out = correct_perspective(img, (size, size), input_pts, output_pts)
    cv2.imwrite(dst_image, out)
    return img.shape[:2]
