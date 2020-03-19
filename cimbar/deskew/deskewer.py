import cv2
import numpy

from cimbar.deskew.scanner import CimbarScanner


def detector(img, dark):
    cs = CimbarScanner(img, dark, 17)
    return cs.scan()


def deskewer(src_image, dst_image, dark):
    img = cv2.imread(src_image)
    res = detector(img, dark)
    print(res)

    if len(res) < 4:
        print('didnt detect enough points! :(')
        return

    ''' given a 1024x1024 image, corners should correspond to:
     (28, 28)
     (996, 28)
     (28, 996)
     (996, 996)
    '''
    # i.e. width is CELL_DIMENSIONS * CELL_SPACING
    top_left, top_right, bottom_left, bottom_right = res
    # print(f'top left: {top_left}, top right: {top_right}, bottom right: {bottom_right}, bottom left: {bottom_left}')

    size = 1024
    input_pts = numpy.float32([top_left, top_right, bottom_right, bottom_left])
    output_pts = numpy.float32([[28, 28], [size-28, 28], [size-28, size-28], [28, size-28]])
    transformer = cv2.getPerspectiveTransform(input_pts, output_pts)
    correct_prespective = cv2.warpPerspective(img, transformer, (size, size))
    cv2.imwrite(dst_image, correct_prespective)
