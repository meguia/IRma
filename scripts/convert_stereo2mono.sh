#!/bin/sh
DIR=$1
for x in $DIR*.pcm; do
  echo "procesing $x"
  ffmpeg -y -loglevel 0 -f s24le -ar 48k -ac 2 -i "$x" -f s24le -ar 48k  -filter_complex "[0:a]channelsplit=channel_layout=stereo:channels=FL[left]" -map "[left]" "${x%.*}_mono.${x##*.}"
  rm "$x"
done
