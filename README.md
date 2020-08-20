### INTRODUCTION | [ABOUT](ABOUT.md) | [CFC](https://github.com/sz3/cfc) | [LIBCIMBAR](https://github.com/sz3/libcimbar)

## cimbar: Color Icon Matrix bar codes

cimbar is a proof-of-concept 2D data encoding format -- much like [QR Codes](https://en.wikipedia.org/wiki/QR_code), [JAB codes](https://jabcode.org/), and [Microsoft's HCCB](https://en.wikipedia.org/wiki/High_Capacity_Color_Barcode).

![an example cimbar code](https://github.com/sz3/cimbar-samples/blob/v0.5/6bit/4color_ecc30_fountain_0.png)

## How it works

Cimbar encodes data in a grid of symbols (or icons). There are 16 possible symbols per tile (position) on the grid, encoding 4 bits per tile. In addition, 2-3 color bits can be encoded per position on the grid, meaning up to 7 total bits per tile.

![4 bit cimbar encoding](https://github.com/sz3/cimbar-samples/blob/v0.5/docs/encoding.png)

There are multiple color schemes:
* "dark" mode -- meant for backlit computer screens, with bright tiles on a black background
* "light" mode -- meant for paper, with dark tiles on a white background

Cimbar was inspired by [image hashing](https://github.com/JohannesBuchner/imagehash/). On a per-tile basis, the cimbar decoder compares the tile against a dictionary of 16 expected tiles -- each of which maps to a 4 bit pattern -- and chooses the one with the closest imagehash, as measured by [hamming distance](https://en.wikipedia.org/wiki/Hamming_distance). Similarly, the decoder will compare the average color of a tile to a dictionary of (ex: 4) expected colors, and choose the one with the closest color.

[Error correction](https://en.wikipedia.org/wiki/Reed%E2%80%93Solomon_error_correction) is applied on the resulting bit stream, and the bit stream itself is interleaved across the image -- that is, adjacent tiles do not contain adjacent data -- to tolerate localized errors in a source image.

## But, does it really work?

The main constraints cimbar must deal with are:
* all tiles in the tileset must be sufficient hamming distance away from each other, where *sufficient* is determined by whether the decoder can consistently place blurry or otherwise imperfect tiles in the correct "bucket".
* all colors in the colorset must be far enough away from each other -- currently as a function of RGB value scaling -- such that color bleeding, reflections, and the like, can be overcome.

In practice, this means that the source image should be around 1000x1000 resolution or greater, with reasonable color correction handled by the camera -- as you'd find in any modern cell phone.

The python cimbar implementation is, like cimbar itself, a research project. It works, but it is not very performant, and does not handle error cases with much grace. [libcimbar](https://github.com/sz3/libcimbar), the C++ implementation, has been much more heavily optimized. The target goals of the proof-of-concept were:
1. achieve data density on the order of _10kb_ per image.
2. validate a theoretical performance (and if possible, an implemented demonstration) of >= _100kb/s_ data transfer from a computer screen to a cell phone, using only animated cimbar codes and the cell phone camera.

## I want numbers!

* a 6-bit cimbar image contains `9300` raw bytes of data, and `7500` bytes with the default error correction level (30)
* for 7-bit cimbar, the respective numbers are `10850` and `8750`
* error correction level is `N/155`. So `ecc=30` corresponds to a `30:125` ratio of error correction bytes to "real" bytes.
	* error correction is (for now) done via Reed Solomon, which contibutes to the rather large ratio of error correction bytes. See [ABOUT](ABOUT.md) for more technical discussion.

## I want to try it!

* Encoding:

```
python -m cimbar.cimbar --encode myinputfile.txt encoded.png
```

* Decoding:

```
python -m cimbar.cimbar encoded.png myoutputfile.txt
```

There are also some utility scripts, such as the one to measure bit errors:

```
python -m cimbar.cimbar --deskew=0 --ecc=0 encoded.png clean.txt
python -m cimbar.cimbar --ecc=0 camera/001.jpg decode.txt
python -m cimbar.grader clean.txt decode.txt
```

## Would you like to know more?

### [ABOUT](ABOUT.md) | [LIBCIMBAR](https://github.com/sz3/libcimbar)

