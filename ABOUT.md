### [INTRODUCTION](https://github.com/sz3/cimbar) | ABOUT | [CFC](https://github.com/sz3/cfc) | [LIBCIMBAR](https://github.com/sz3/libcimbar)

## What is cimbar?

cimbar is a proof-of-concept 2D data encoding format -- much like [QR Codes](https://en.wikipedia.org/wiki/QR_code), [JAB codes](https://jabcode.org/), and [Microsoft's HCCB](https://en.wikipedia.org/wiki/High_Capacity_Color_Barcode).

## Why did you do this?

The inspirations were:
1. image hashing, e.g. https://github.com/JohannesBuchner/imagehash
2. [txqr](https://github.com/divan/txqr), which uses animated QR codes to transfer data over the phone camera
3. [Microsoft's HCCB](https://en.wikipedia.org/wiki/High_Capacity_Color_Barcode)

`txqr` achieved a transfer speed of `25kb/s` (though this seems to be a burst rate), which seems very good for QR codes. But, with the general feeling of "we can do better than this!", I decided to look into the problem.

It's worth noting that I would not have created cimbar if HCCB was open source -- I would instead have tried to use it for this purpose. I *might* have written an open source implementation of HCCB, but it wasn't (and still isn't) clear to me what Microsoft wants to do with the technology.

My experiments (including trying and failing to get `jabcode`s to work to my liking) led to a new bar code format. Covid19-induced lockdown led to me spending more time on it than I'd originally envisioned.

## Is three projects a lot for a proof of concept?

* the three projects are:
1. [cimbar](https://github.com/sz3/cimbar) (you are here) -- focused on research and design. Not very fast.
2. [libcimbar](https://github.com/sz3/libcimbar) -- focused on implementation. C++ code. Pretty fast. Also includes a data envelope format built on fountain codes.
3. [cfc](https://github.com/sz3/libcimbar) -- focused on usage. This is a barebones android app that uses libcimbar to receive files over the camera lens.

My conclusion was that if I was going to create a proof-of-concept implementation of a new bar code format, I would need to *prove* -- demonstrate -- a use case, implausible or otherwise. In this case, the use case was the initial motivation -- hit sustained 100kb/s data transfer rates, or, if not, demonstrate that it was clearly possible (or impossible -- and call the project a bust). So, that is what I did.

## Is there a spec?

Not yet. The project is -- at this point -- just a proof-of-concept. It's not clear to me that cimbar is any better for data density + reliability than HCCB, or better than the myriad of unfinished attempts at color QR codes that are floating around, or (...). It could be a technological dead end. But perhaps with more refinement it might be interesting?

## Notable open questions, concerns, and ideas:

* the symbol set is not optimal. There are 16, and their image hashes are all reasonable hamming distance from each other, and do *ok* when upscaled... but I drew the initial 40 or so candidates by hand in kolourpaint, and paired down the set to 16 by experimentation.
	* 32 distinct tiles (5 bits) be possible for 8x8 tiles

* the tile size was chosen arbitrarily -- specifically, it's 8x8 because most of the imagehash algorithms operate on an 8x8 tile
	* is 8x8 optimal? How might one find out?

* the grid size (1024x1024) was chosen semi-arbitrarily -- I wanted it to be a square under 1080x1080 (for monitor resolution reasons).
	* is a square grid optimal?
	* would a smaller overall resolution satisfy more use cases?

* how viable is the (very simple) color decoding logic?
	* notably, no color correction is currently done -- the camera is expected to do the heavy lifting
	* color decoding in cimbar has an inherent limitation in that colors must be constrained away from the background color.
		* for example, blue (0x0000FF) is a bad fit for dark mode cimbar, since it tends to blend together with black.
		* when the colors blend into the background color, symbol decoding is negative affected, and error rates explode
	* 4-color cimbar (2 color bits) seems entirely reasonable
		* most tests have been done with the dark mode palette, but light mode should work as well
	* 8-color cimbar (3 color bits) is possible, at least in dark mode
		* probably light mode as well, but a palette will need to be found
	* 16-color cimbar does not seem possible with the current color decoding logic
		* but with pre-processing for color correction and a perceptual color diff (like CIE76), ... maybe?
		* this may be wishful thinking.

* Reed Solomon was chosen for error correction due how ubiquitous its implementations are.
	* it isn't a perfect fit. Most cimbar errors are 1-3 flipped bits at a time -- Reed Solomon doesn't care if one bit flipped or eight did -- a bad byte is a bad byte.
	* Something built on LDPC would likely be better.

* the focus on computer screens has surely overlooked problems that come from paper/printed/e-paper surfaces
	* using a black background ("dark mode") came out of getting better results from backlit screens
	* notably, there are some threshold parameters and color averaging heuristics that will (probably) need to be re-tuned for "light mode" cimbar
	* curved surfaces are a can of worms I didn't want to open -- there are some crazy ideas that could be pursued there, but they may not be worth the effort

* should cimbar include "metadata" to tell the decoder what it's trying to decode -- ECC level, number of colors, (grid size...?)
	* the bottom right corner of the image seems like the logical place for this.
	* a slightly smaller 4th anchor pattern could give us 11 tiles (44 bits?) to work with for metadata, which is not a lot, but probably enough.


## Would you like to know more?

### [INTRODUCTION](https://github.com/sz3/cimbar) | [LIBCIMBAR](https://github.com/sz3/libcimbar)

