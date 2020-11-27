#!/usr/bin/env python3

import sys
import argparse
import numpy as np
import acoustic_field.soundscape as sc

parser = argparse.ArgumentParser()

parser.add_argument('-nchan', type=int, default=2, help="Number of Channels")
parser.add_argument('-nbytes', type=int, default=2, help="Number of Bytes")
parser.add_argument('-window', type=int, default=1024, help="Window Size")
parser.add_argument('-tstep', type=int, default=468, help="Window Size")

args = parser.parse_args()

pkeys=['aci','bi','ndsi','aei','adi','hs']

dump = np.frombuffer(sys.stdin.buffer.read(), dtype='u1', count=-1)
nsamples=dump.shape[0]//(args.nchan*args.nbytes)
if args.nbytes==4:
	data=np.reshape(dump.view(np.int32),(nsamples,args.nchan))
elif args.nbytes==2:
	data=np.reshape(dump.view(np.int16),(nsamples,args.nchan))
elif args.nbytes==1:
    data=np.reshape(dump.view(np.int8),(nsamples,args.nchan))
else:
	raise Exception("Only 4,2 or 1 bytes allowed")

spec = sc.spectrogram(data[:,0],args.window,0)
ind = sc.indices(spec,args.tstep)
for k in pkeys:
	print(k.upper())
	print(ind[k][0])
