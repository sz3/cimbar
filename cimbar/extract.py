import sys
from cimbar.deskew.deskewer import deskewer


def main():
    src_image = sys.argv[1]
    dst_image = sys.argv[2]
    deskewer(src_image, dst_image, dark=True)


if __name__ == '__main__':
    main()
