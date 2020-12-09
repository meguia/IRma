#!/usr/bin/env python3
import sys
import yaml
import requests
import argparse
import numpy as np
import acoustic_field.soundscape as sc
from datetime import datetime, timedelta

now = datetime.now()

parser = argparse.ArgumentParser()

send_parser = parser.add_mutually_exclusive_group(required=False)
send_parser.add_argument('--send', dest='send', action='store_true')
send_parser.add_argument('--no-send', dest='send', action='store_false')
parser.set_defaults(send=True)
#parser.add_argument('-send', type=bool, default=True, help="Send to Google Drive")
args = parser.parse_args()

with open('/home/pi/options.yaml') as file:
	opt = yaml.load(file, Loader=yaml.FullLoader)

dump = np.frombuffer(sys.stdin.buffer.read(), dtype='u1', count=-1)
nsamples=dump.shape[0]//(opt['nchan']*opt['nbytes'])
nmax = 2**(opt['nbytes']*8-1)
print(nsamples)
if opt['nbytes']==4:
	data=np.reshape(dump.view(np.int32)/nmax,(nsamples,opt['nchan'])).astype('float64') 
elif opt['nbytes']==2:
	data=np.reshape(dump.view(np.int16)/nmax,(nsamples,opt['nchan'])).astype('float32')
elif opt['nbytes']==1:
    data=np.reshape(dump.view(np.int8)/nmax,(nsamples,opt['nchan'])).astype('float32')
else:
	raise Exception("Only 4,2 or 1 bytes allowed")

with open('/home/pi/acoustic_field/config/defaults.yaml') as file:
    par = yaml.load(file, Loader=yaml.FullLoader)

if par['hipass']:
	data[:,0] = soundscape.hipass_filter(data[:,0],**par['Filtering'])

spec = sc.spectrogram(data[:,0],**par['Spectrogram'])
# recalculate values of windows based on the number of samples 
HW = int(np.floor(par['Indices']['window']*par['sr']/(2*par['windowSize'])))
par['Indices']['half_window'] = HW
NOWF = int(np.floor(spec['nsamples'] / par['windowSize']))
par['Indices']['number_of_windows'] = int(np.floor((NOWF-HW)/HW))

# compute time intervals
ind = sc.indices(spec,**par['Indices'])
dur = ind['nsamples']/par['sr']
indt = dur - ind['t']
tlist = [now - timedelta(seconds=t.item()) for t in indt]

# write to stdout
par_str = 'time=' + ",".join([t.strftime("%Y-%m-%dT%H:%M:%SZ") for t in tlist])
for k in opt['pkeys']:
	par_str += '&' + k.upper() + '=' + ",".join([str(np.around(s,decimals=3)) for s in ind[k][0,:]]) 
print(par_str)

# send to google drive
if args.send:
	req = requests.get(opt['request_url'] + '?' + par_str)
	print(req)

#write to logfile
with open(opt['logfile'], "a") as fp:
	for n,t in enumerate(tlist):
		csvline = t.strftime("%Y-%m-%dT%H:%M:%SZ") + ","
		csvline += ",".join([str(np.around(ind[k][0,n],decimals=3)) for k in opt['pkeys']]) + "\n"
		fp.write(csvline)	
fp.close() 
