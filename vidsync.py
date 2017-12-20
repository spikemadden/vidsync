import subprocess
import sys
import StringIO
import math
import time
import os

import numpy

from argparse import ArgumentParser

from PIL import Image
from PIL import ImageDraw

from skimage import img_as_float
from skimage.measure import compare_mse

def stream_to_jpeg(f):
    buf = ""
    jpeg_ending = '\xff\xd9'
    while True:
        while jpeg_ending in buf:
            pos = buf.index(jpeg_ending)
            temp = StringIO.StringIO()
            temp.write(buf[:pos+len(jpeg_ending)])
            temp.seek(0)
            yield Image.open(temp)
            buf = buf[pos + len(jpeg_ending):]
        chunk = f.read(4096)
        if not chunk:
            break
        buf += chunk

def setup_parser(parser):
    parser.add_argument("file1")
    parser.add_argument("file2")
    parser.add_argument("-o", "--offset", type=int)
    parser.add_argument("-n", "--parts", type=int)
    parser.add_argument("-d", "--directory")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--save", action="store_true")

parser = ArgumentParser()
setup_parser(parser)
args = parser.parse_args()

vid1 = args.file1
vid2 = args.file2

# command line defaults
offset = 0
parts = 10
directory = "results"

if args.offset is not None:
    offset = args.offset
if args.parts is not None:
    parts = args.parts
if args.directory is not None:
    directory = args.directory

# create output directory
if not os.path.exists(directory):
    if args.verbose:
        print 'creating output directory'
    os.makedirs(directory)

# time of two files in seconds
if args.verbose:
    print 'ffprobe: calculating movie duration in seconds'

# video 1 duration in seconds
ffprobe_vid1_duration = subprocess.Popen(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=duration', '-of', 'default=noprint_wrappers=1:nokey=1', vid1], stdout=subprocess.PIPE)

# video 2 duration in seconds
ffprobe_vid2_duration = subprocess.Popen(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=duration', '-of', 'default=noprint_wrappers=1:nokey=1', vid2], stdout=subprocess.PIPE)

# framerate of two files
if args.verbose:
    print 'ffprobe: extracting framerate from both videos'

# video 1 framerate
ffprobe_vid1_framerate = subprocess.Popen(['ffprobe', '-v', '0', '-of', 'csv=p=0', '-select_streams', '0', '-show_entries', 'stream=r_frame_rate', vid1], stdout=subprocess.PIPE)

# video 2 framerate
ffprobe_vid2_framerate = subprocess.Popen(['ffprobe', '-v', '0', '-of', 'csv=p=0', '-select_streams', '0', '-show_entries', 'stream=r_frame_rate', vid2], stdout=subprocess.PIPE)

vid1_duration = round(float(ffprobe_vid1_duration.communicate()[0]))
vid2_duration = round(float(ffprobe_vid2_duration.communicate()[0]))

vid1_framerate_fraction = ffprobe_vid1_framerate.communicate()[0].split('/')
vid1_framerate_fraction = map(float, vid1_framerate_fraction)
vid1_framerate = vid1_framerate_fraction[0] / vid1_framerate_fraction[1]

vid2_framerate_fraction = ffprobe_vid2_framerate.communicate()[0].split('/')
vid2_framerate_fraction = map(float, vid2_framerate_fraction)
vid2_framerate = vid2_framerate_fraction[0] / vid2_framerate_fraction[1]

if args.verbose:
    print 'video 1 duration is ' + str(vid1_duration) + ' seconds'
    print 'video 2 duration is ' + str(vid2_duration) + ' seconds'

if args.verbose:
    print 'video 1 framerate is ' + str(vid1_framerate)
    print 'video 2 framerate is ' + str(vid2_framerate)


vid1_frame_period = vid1_duration / parts
vid2_frame_period = 1.0 / vid2_framerate

if args.verbose:
    print 'video 1 frame period is ' + str(vid1_frame_period)
    print 'video 2 frame period is ' + str(vid2_frame_period)

vid1_timestamp = -1 * vid1_frame_period
vid2_timestamp = -1 * vid2_frame_period

every_n_seconds = 1.0 / vid1_frame_period

# extract 1 frame every n seconds from video 1
p = subprocess.Popen(['ffmpeg', '-i', vid1, '-loglevel', 'fatal',
                                '-r', str(every_n_seconds),
                                '-f', 'mjpeg',
                                '-qscale:v', '2',
                                '-vf', 'scale=320:180',
                                'pipe:'], stdout=subprocess.PIPE)

# extract every frame from video 2
p2 = subprocess.Popen(['ffmpeg', '-i', vid2, '-loglevel', 'fatal',
                                '-f', 'mjpeg',
                                '-qscale:v', '2',
                                '-vf', 'scale=320:180', 'pipe:'], stdout=subprocess.PIPE)

vid1_images = stream_to_jpeg(p.stdout)
vid2_images = stream_to_jpeg(p2.stdout)

if not vid1_images or not vid2_images:
    print 'could not open ffmpeg'
    sys.exit(1)

# ffmpeg produces an extra frame at beginning
next(vid1_images, 0)
next(vid2_images, 0)

total_offset = 0

leniency = 0.2 * vid1_frame_period

for img1 in vid1_images:
    vid1_timestamp += vid1_frame_period

    best_mse = float('inf')
    closest_timestamp = 0
    closest_img = None

    # skip up to frames near vid1 frame
    # offset helps resync movies
    while (vid2_timestamp - total_offset < vid1_timestamp + offset - leniency):
        next(vid2_images, 0)
        vid2_timestamp += vid2_frame_period

    total_offset += offset
    offset = 0

    # offset will always be 0 here
    while (vid2_timestamp - total_offset <= vid1_timestamp + offset + leniency):
        try:
            img2 = next(vid2_images)
            vid2_timestamp += vid2_frame_period
        except:
            break

        # do comparisons and save best
        mse = compare_mse(img_as_float(img1), img_as_float(img2))

        #print 'mse for ' + str(vid2_timestamp) + ' is ' + str(mse)

        if mse < best_mse:
            closest_img = img2
            closest_timestamp = vid2_timestamp
            best_mse = mse

    if closest_img:

        # how far from ideal match (+ or -)
        offset = closest_timestamp - (vid1_timestamp + total_offset)

        img1_ts = time.strftime('%H.%M.%S', time.gmtime(vid1_timestamp))
        closest_ts = time.strftime('%H.%M.%S', time.gmtime(closest_timestamp))
        best_mse = round(best_mse, 3)

        if args.verbose:
            print 'best match was found at ' + closest_ts
            print 'mse: ' + str(best_mse)

        if args.save:
            img1.save(directory + '/' + img1_ts + '_vid1.jpg')
            closest_img.save(directory + '/' + closest_ts + '_vid2.jpg')

        # text on image from vid1
        draw = ImageDraw.Draw(img1)
        draw.text((0, 0), img1_ts, (255,255,255))

        # text on closest image from vid2
        draw = ImageDraw.Draw(closest_img)
        draw.text((0, 0), closest_ts, (255,255,255))
        draw.text((0, 10), str(best_mse), (255, 255, 255))

        # combine images
        imgs = [img1, closest_img]
        imgs_comb = numpy.vstack((numpy.asarray(i) for i in imgs))
        imgs_comb = Image.fromarray(imgs_comb)

        imgs_comb.save(directory + '/' + closest_ts + '_combined.jpg')
