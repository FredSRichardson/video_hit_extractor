#!/usr/bin/env python3

# This scripts takes an input image and an input video (that are
# assumed to have exactly the same pixel dimensions) and a bounding
# box specifying the region in the image to search for in the video.
# The search is done with tight parameters because the video is
# assumed to come from a video game with very little analog noise in
# the data stream.  Otherwise we might be talking about a somewhat
# difficult machine learning problem with fancy statistical models
# (and likely poorer performance than this approach).
#
# The detection approach comes from the internet and is very clever.
# Basically you subtract each video image from from the input image
# and check to see if the resulting frame is black.  The input image
# is actually treated like a single frame video that is looped to
# match the duration of the input video - so essentially we are
# sbutracting regions of two videos and running a black frame
# detector.

import argparse, re, os

def parse_detect(line):
    if line.find('[Parsed_blackframe') != 0:
        return None
    ret = {}
    for e in line.split():
        kv = e.split(':')
        if len(kv) != 2:
            continue
        ret[kv[0]] = kv[1]
    return ret

def parse_proc_output(proc):
    all_hits = []

    hits = []
    for line in proc.stderr:
        line = line.decode('utf-8').strip()
        res = parse_detect(line)
        if res is not None:
            hits.append(res)
        else:
            if hits:
                all_hits.append(hits)
                hits = []

    if hits:
        all_hits.append(hits)
        hits = []
        
    return all_hits

parser = argparse.ArgumentParser(description="Search for frames matching an image at a particular location")
parser.add_argument('-v', '--verbose', action='store_true',
                    help='increase output verbosity')
parser.add_argument('-X', type=int,
                    help='X location of upper-left target region point', 
                    required=True)
parser.add_argument('-Y', type=int,
                    help='Y location of upper-left target region point', 
                    required=True)
parser.add_argument('-W', type=int,
                    help='Width of target region', 
                    required=True)
parser.add_argument('-H', type=int,
                    help='Height of target region', 
                    required=True)
parser.add_argument('input_video', type=str,
                    help='Input video file')
parser.add_argument('input_image', type=str,
                    help='Input target image file (must match size of video frames)')
parser.add_argument('output_time_segments', type=str,
                    help='Output file containing list of time segments')

args = parser.parse_args()

import ffmpeg

video_stream = ffmpeg.input(args.input_video)
image_stream = ffmpeg.input(args.input_image, r=1, loop=1)

video_stream = ffmpeg.crop(video_stream, args.X, args.Y, args.W, args.H, exact=1)
image_stream = ffmpeg.crop(image_stream, args.X, args.Y, args.W, args.H, exact=1)
proc = (
    ffmpeg
    .filter([video_stream, image_stream], 'blend', 'difference', shortest=1)
    .filter('blackframe', 98, 20)
    .output('-', format='null')
    .run_async(pipe_stdout=False, pipe_stderr=True)
)
      
# Watch for lines like this:
#   [Parsed_blackframe_3 @ 0x5e0e58858880] frame:4696 pblack:98 pts:78267 t:78.267000 type:I last_keyframe:4696
all_hits = parse_proc_output(proc)

# Now just grab the first and last time for each segment:
segs = []
for h in all_hits:
    st_sec = float(h[0]['t'])
    en_sec = float(h[-1]['t'])
    segs.append( (st_sec, en_sec) )

nsegs = len(segs)
print(f'{nsegs} detected in input video')

with open(args.output_time_segments, 'w') as ofp:
    for stt, ent in segs:
        ofp.write(f'{stt} {ent}\n')

