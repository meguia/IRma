#!/usr/bin/env python3

import sys
import yaml
import requests
import argparse
import numpy as np
import acoustic_field.soundscape as sc
from datetime import datetime, timedelta

parser = argparse.ArgumentParser()

parser.add_argument('-d', type=str, default=None, help="Date and Time")
parser.add_argument('-nchan', type=int, default=2, help="Number of Channels")
parser.add_argument('-nbytes', type=int, default=2, help="Number of Bytes")

args = parser.parse_args()
request_url = 'https://script.google.com/macros/s/AKfycbxz79-99xkm4EpF0bRFuTgjjD0Dvzf3mgsnWZKwratUTklIQxKe/exec'
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

if par['hipass']:
	data[:,0] = soundscape.hipass_filter(data[:,0],**par['Filtering'])

spec = sc.spectrogram(data[:,0],**par['Spectrogram'])
# recalculate values of windows based on the number of samples 
HW = int(np.floor(par['Indices']['window']*par['sr']/(2*par['windowSize'])))
par['Indices']['half_window'] = HW
NOWF = int(np.floor(spec['nsamples'] / par['windowSize']))
par['Indices']['number_of_windows'] = int(np.floor((NOWF-HW)/HW))

ind = sc.indices(spec,**par['Indices'])
dur = ind['nsamples']/par['sr']
indt = dur - ind['t']
datestr = args.d.split('/')[-1].split('.')[0]
now = datetime.strptime(datestr,'%Y_%m_%d_%H_%M_%S')
tlist = [now - timedelta(seconds=t.item()) for t in indt]

par_str = 'time=' + ",".join([t.strftime("%Y-%m-%dT%H:%M:%SZ") for t in tlist])
for k in pkeys:
	par_str += '&' + k.upper() + '=' + ",".join([str(np.around(s,decimals=3)) for s in ind[k][0,:]]) 
print(par_str)
req = requests.get(request_url + '?' + par_str)
print(req)




