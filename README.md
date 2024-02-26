### INTRODUCTION | [ABOUT](ABOUT.md) | [CFC](https://github.com/sz3/cfc) | [LIBCIMBAR](https://github.com/sz3/libcimbar)

## cimbar: Color Icon Matrix bar codes

cimbar is a proof-of-concept 2D data encoding format -- much like [QR Codes](https://en.wikipedia.org/wiki/QR_code), [JAB codes](https://jabcode.org/), and [Microsoft's HCCB](https://en.wikipedia.org/wiki/High_Capacity_Color_Barcode).

<p align="center">
<img src="https://github.com/sz3/cimbar-samples/blob/v0.6/b/4cecc30f.png" width="70%" title="A non-animated mode-B cimbar code" >
</p>

## How it works

Cimbar encodes data in a grid of symbols (or icons). There are 16 possible symbols per tile (position) on the grid, encoding 4 bits per tile. In addition, 2-3 color bits can be encoded per position on the grid, meaning up to 7 total bits per tile.

![4 bit cimbar encoding](https://github.com/sz3/cimbar-samples/blob/v0.5/docs/encoding.png)

There are multiple color schemes:
* "dark" mode -- meant for backlit computer screens, with bright tiles on a black background
* "light" mode -- meant for paper, with dark tiles on a white background

Cimbar was inspired by [image hashing](https://github.com/JohannesBuchner/imagehash/). On a per-tile basis, the cimbar decoder compares the tile against a dictionary of 16 expected tiles -- each of which maps to a 4 bit pattern -- and chooses the one with the closest imagehash, as measured by [hamming distance](https://en.wikipedia.org/wiki/Hamming_distance). Similarly, the decoder will compare the average color of a tile to a dictionary of (ex: 4) expected colors, and choose the one with the closest color.

[Error correction](https://en.wikipedia.org/wiki/Reed%E2%80%93Solomon_error_correction) is applied on the resulting bit stream, and the bit stream itself is interleaved across the image -- that is, adjacent tiles do not contain adjacent data -- to tolerate localized errors in a source image.

## But, does it really work?

Yes, and I can prove it. :)

* encoder: https://cimbar.org (uses [libcimbar](https://github.com/sz3/libcimbar))
* decoder Android app: https://github.com/sz3/cfc/releases/latest

The main constraints cimbar must deal with are:
* all tiles in the tileset must be sufficient hamming distance away from each other, where *sufficient* is determined by whether the decoder can consistently place blurry or otherwise imperfect tiles in the correct "bucket".
* all colors in the colorset must be far enough away from each other -- currently as a function of RGB value scaling -- such that color bleeding, reflections, and the like, can be overcome.

Cimbar is designed to deal with some lossiness. In practice, the source image should be around 700x700 resolution or greater, in focus, and with *some* color correction handled by the camera -- as you'll hopefully find in any modern cell phone.

This python cimbar implementation is a research project. It works, but it is slow, and does not handle error cases with much grace. [libcimbar](https://github.com/sz3/libcimbar), the C++ implementation, has been much more heavily optimized and tested. The target goals of the proof-of-concept were:
1. achieve data density on the order of _10kb_ per image.
2. validate a theoretical performance (and if possible, an implemented demonstration) of >= _100kb/s_ data transfer (800 kilobits/second) from a computer screen to a cell phone, using only animated cimbar codes and the cell phone camera.

## I want numbers!

* a `mode B` (8x8, 4-color, 30/155 ecc, 6-bits-per-tile) cimbar image contains `9300` raw bytes of data, and `7500` bytes with the default error correction level (30)
* for the old `mode 8C` (8x8, 8-color, 7-bit) cimbar, the respective numbers are `10850` and `8750`
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
python -m cimbar.cimbar /tmp/encoded.png -o /tmp/myoutputfile.txt
```

There are also some utility scripts, such as the one to measure bit errors:

```
python -m cimbar.cimbar encoded.png -o clean.txt --deskew=0 --ecc=0
python -m cimbar.cimbar camera/001.jpg -o decode.txt --ecc=0
python -m cimbar.grader clean.txt decode.txt
```

## Would you like to know more?

### [ABOUT](ABOUT.md) | [LIBCIMBAR](https://github.com/sz3/libcimbar)

