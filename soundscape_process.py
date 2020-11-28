#!/usr/bin/env python3

import sys
import yaml
import argparse
import numpy as np
import acoustic_field.soundscape as sc

parser = argparse.ArgumentParser()

parser.add_argument('-nchan', type=int, default=2, help="Number of Channels")
parser.add_argument('-nbytes', type=int, default=2, help="Number of Bytes")
parser.add_argument('-twin', type=int, default=5, help="Window Duration in seconds")


args = parser.parse_args()

pkeys=['aci','bi','ndsi','aei','adi','hs','ht','sc','db']
nmax = 2**(args.nbytes*8-1)

dump = np.frombuffer(sys.stdin.buffer.read(), dtype='u1', count=-1)
nsamples=dump.shape[0]//(args.nchan*args.nbytes)
if args.nbytes==4:
	data=np.reshape(dump.view(np.int32)/nmax,(nsamples,args.nchan)).astype('float64') 
elif args.nbytes==2:
	data=np.reshape(dump.view(np.int16)/nmax,(nsamples,args.nchan)).astype('float32')
elif args.nbytes==1:
    data=np.reshape(dump.view(np.int8)/nmax,(nsamples,args.nchan)).astype('float32')
else:
	raise Exception("Only 4,2 or 1 bytes allowed")

with open('acoustic_field/config/defaults.yaml') as file:
    par = yaml.load(file, Loader=yaml.FullLoader)

#tstep = int(np.around(args.twin*par['sr']/par['windowSize']))

if par['hipass']:
	data[:,0] = soundscape.hipass_filter(data[:,0],**par['Filtering'])

spec = sc.spectrogram(data[:,0],**par['Spectrogram'])
ind = sc.indices(spec,**par['Indices'])
for n,t in enumerate(ind['t']):
    line = 'time={0:.2f}'.format(t)
    for k in pkeys:
        line += ' {0}={1:.2f}'.format(k.upper(),ind[k][0,n])
    print(line)
