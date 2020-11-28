#!/bin/sh
unset IFS
inotifywait -m -e close_write \
  --timefmt '%Y_%m_%d|%H:%M:%S' \
  --format '%w %f %e %T' \
  /home/pi/Recordings \
| while read dir filename event datetime; do
  echo "Procesando: $dir$filename $datetime"	
  ffmpeg -y -loglevel 0 -f s24le -ar 48k -ac 2 -i $dir$filename -f s16le - |  /home/pi/soundscape_process.py   
done

