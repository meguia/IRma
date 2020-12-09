#!/bin/bash
PREFIX=${1:-rec}
DUR=${2:-60}
FOLDER=${3:-Recordings/}
BLOCK=$(( DUR * 192000 ))
FILENAME=$FOLDER$PREFIX$(date +'_%Y_%m_%d_%H_%M_')
echo "Starts recording mono at $FILENAME in blocks of $DUR seconds"
arecord -t raw -D lp -c1 -r 48000 -f S32_LE | split -d -a 4 -b $BLOCK --filter=' ffmpeg -y -loglevel 0 -f s32le -ar 48k -ac 1 -i pipe: -f s24le $FILE.pcm' - $FILENAME &
