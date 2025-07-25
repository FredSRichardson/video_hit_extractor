#!/usr/bin/env python3

import argparse, re, os

# The general approach of this scripts is to take a bunch of intput
# segment lists, read them in, sort them by start time, pad the times
# and merge segments that are close in time, extract a video for each
# resulting time segment and then merge all the videos.
# 
# I attempting to do the extraction and merging as a single ffmpeg
# filter and I could not get it to work reliably, so I had to do this
# the clunky way that actually works.

# bad and broken algo... look at all gaps first..
def pad_merge_segs(segs, pad, fill):
    # pad all segments:
    psegs = []
    for st_sec, en_sec in segs:
        # Pad segments by 0.5 seconds and clamp to start time of video:
        st_sec = max(st_sec - pad, 0.0)
        # Not sure how to clamp end-time - nened duration of video...
        en_sec = en_sec + pad
        psegs.append( (st_sec, en_sec) )
    segs = psegs
    psegs = None

    # Find all gaps to fill:
    nsegs = len(segs)
    do_fill = []
    for iseg in range(1, nsegs):
        _, p_en_sec = segs[iseg - 1]
        stt_sec, _ = segs[iseg]
        do_fill.append( stt_sec - p_en_sec <= fill)
    # Nothing to merge last segment with (if it wasn't merged with
    # prior segments):
    do_fill.append(False)

    # Now we have to merge all segments in a sequence that needs to be filled:
    out_segs = []
    iseg = 0
    while iseg < nsegs:
        i_stt, i_ent = segs[iseg]
        if not do_fill[iseg]:
            out_segs.append( (i_stt, i_ent) )
            iseg += 1
            continue
        # Figure out how many segs to merge:
        jmerge = None
        jmerge_ent = None
        for jseg in range(iseg+1, nsegs):
            # do we fill with the *previous* segment?
            if do_fill[jseg - 1]:
                _, j_ent = segs[jseg]
                jmerge = jseg
                jmerge_ent = j_ent
            else:
                break
        assert jmerge is not None, 'ERROR: we should have found at least one segment to merge'
        out_segs.append( (i_stt, jmerge_ent) )
        iseg = jmerge + 1
    return out_segs


parser = argparse.ArgumentParser(description="Search for frames matching an image at a particular location")
parser.add_argument('--pad', type=float,
                    help='Number of seconds to pad each detected segment by', 
                    default=0.5)
parser.add_argument('--fill', type=float,
                    help='Merge segments with time gaps less than or equal to the fill value', 
                    default=1.0)
parser.add_argument('input_seg_list', nargs='+', type=str,
                    help='Input list with lines of start and end times')
parser.add_argument('input_video', type=str,
                    help='Input video file')
parser.add_argument('output_video', type=str,
                    help='Output video of matching segments')

args = parser.parse_args()

import ffmpeg

tsegs = []
for fname in args.input_seg_list:
    with open(fname) as ifp:
        for line in ifp:
            e = line.split()
            assert len(e) == 2, f'ERROR: expected only two elements on each line of "{fname}": {line.strip()}'
            stt, ent = (float(e[0]),  float(e[1]))
            if ent == stt:
                continue
            tsegs.append( (stt, ent) )

tsegs =  sorted(tsegs, key=lambda x: x[0])

if False:
    print(f'{len(tsegs)} before padding and merging:')
    for st_sec, en_sec in tsegs:
        print(f'{st_sec:.3f} {en_sec:.3f}')
    print()    

print('Padding and merging segments')
tsegs = pad_merge_segs(tsegs, pad=args.pad, fill=args.fill)

if False:
    print(f'{len(tsegs)} after padding and merging:')
    for st_sec, en_sec in tsegs:
        print(f'{st_sec:.3f} {en_sec:.3f}')
    print()    

nsegs = len(tsegs)
print(f'{nsegs} segments after padding (pad={args.pad:.3f}s) and merging (fill={args.fill:.3f}s) ...')

files_to_clean = []

list_file = f'{args.output_video}-list.txt'
files_to_clean.append(list_file)
with open(list_file, 'w') as ofp:
    for iseg, seg in enumerate(tsegs):
        st_sec, en_sec = seg
        dur_sec = en_sec - st_sec
        ofname = f'{args.output_video}-{iseg:05d}.mp4'
        files_to_clean.append(ofname)
        ofp.write(f"file '{os.path.basename(ofname)}'\n")
        try:
            (
                ffmpeg.input(args.input_video, ss=st_sec)
                .output(ofname, t=dur_sec, format='mp4', loglevel='quiet')
                .run(overwrite_output=True)
            )
            print(f"File trimed successfully to start_time={st_sec:.3f} end_time={en_sec:.3f} and written to: {ofname}")
        except ffmpeg.Error as e:
            print(f"Error during trimming: {e.stderr.decode()}")

output_file = f'{args.output_video}.mp4'
try:
    (
        ffmpeg
        .input(list_file, f='concat', safe=0)
        .output(output_file, c='copy', format='mp4', loglevel='quiet')
        .run(overwrite_output=True)
    )
    print(f"Files concatenated successfully to {output_file}")
except ffmpeg.Error as e:
    print(f"Error during concatenation: {e}")

# Cleanup temp files:
for fname in files_to_clean:
    if os.path.exists(fname):
        os.remove(fname)
