# vidsync

This program compares two video files and analyzes how similar they are. This program uses `ffmpeg` to pull frames from each video and compares them using `scikit-image`.

The program produces a combined image for each of the corresponding scenes along with the [mean square error between](http://scikit-image.org/docs/stable/api/skimage.measure.html#skimage.measure.compare_mse) the images.

## Usage

`python vidsync.py [-h] [-o --offset] [-n --parts] [-d --directory] [--verbose] [--save] file1 file2`

positional arguments:
* `file1` - the first video file
* `file2` - the second video file

optional arguments:
* `-h`, `--help` shows help and usage message
* `-o`, `--offset` the number of seconds that file2 is offset compared to file1 - defaults to `0`, can be positive or negative
* `-n`, `--parts` the number of parts that video 1 is split into - defaults to `10`
* `-d`, `--directory` the results directory that stores all the images - defaults to `results`
* `--verbose` run with verbose messages
* `--save` saves the individual images from both video 1 and 2, along with the combined image

## Getting Started

Python 2.7.14

Use pip to install the following packages.

### Requirements
```
numpy
Pillow
scikit-image
```
