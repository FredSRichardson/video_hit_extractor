#! /bin/bash -e

if [ $# -ne 2 ]; then
    echo "Usage: $0 <video> <output-pfx>"
    exit -1
fi

input_vid=$1 && shift
output_pfx=$1 && shift

# Get skill bar hits:
tgt_file=${output_pfx}_skill_hits.txt
if [ ! -e $tgt_file ]; then
    ./detect_hits.py -X 1227 -Y 106 -W 572 -H 65 $input_vid pngs/d2-skills-bar.png $tgt_file
else
    echo "$tgt_file: file already - delete to regenerate"
fi

# Get inventory bar hits:
tgt_file=${output_pfx}_inv_hits.txt
if [ ! -e $tgt_file ]; then 
    ./detect_hits.py -X 1226 -Y 104 -W 575 -H 70 $input_vid pngs/d2-inv-bar.png $tgt_file
else
    echo "$tgt_file: file already - delete to regenerate"
fi

# Get stats bar hits:
tgt_file=${output_pfx}_stats_hits.txt
if [ ! -e $tgt_file ]; then 
    ./detect_hits.py -X 120  -Y 102 -W 574 -H 69 $input_vid pngs/d2-stats-bar.png $tgt_file
else
    echo "$tgt_file: file already - delete to regenerate"
fi

# Create a new video of all skills, stats and inventory bar hits:
tgt_file=${output_pfx}_skills_stats_inv
if [ ! -e $tgt_file.mp4 ]; then
    ./extract_and_merge.py \
        ${output_pfx}_skill_hits.txt \
        ${output_pfx}_inv_hits.txt \
        ${output_pfx}_stats_hits.txt \
        $input_vid \
        $tgt_file
else
    echo "$tgt_file: file already - delete to regenerate"
fi

tgt_file=${output_pfx}_skills_stats
if [ ! -e $tgt_file.mp4 ]; then
    ./extract_and_merge.py \
        ${output_pfx}_skill_hits.txt \
        ${output_pfx}_stats_hits.txt \
        $input_vid \
        $tgt_file
else
    echo "$tgt_file: file already - delete to regenerate"
fi
