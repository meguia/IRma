import numpy as np
import sounddevice as sd
from scipy.io import wavfile

def time_rec(filerec,duration,delay=0,chanin=[1],fs=48000,sdevice=None,write_wav=True):
    '''
    it records audio for a specified duration using an arbitrary number of input channels given by chanin (list)
    in file filerec.
    '''
    # add clipping alert and dummy run option
    if sdevice is not None:
        sd.default.device = sdevice
    sd.default.samplerate = fs
    # loop over repeat
    rec = sd.rec(int(duration*fs),samplerate=fs,mapping=chanin,dtype='float64') # records with 64 bits for processing
    sd.wait() # wait 
    print('finished')
    if write_wav:
        wavfile.write(filerec + '.wav',fs,rec.astype(np.float32)) # saves the recorded array to WAV with 32-bit float
    # end loop
    return rec

def play_rec(fplay,filerec,delay=0,chanout=[1],chanin=[1],revtime=2.0,sdevice=None,write_wav=True,fs=48000):
    '''
    function to play the mono wav file fplay through the output channels chanout (list)
    and record it simultaneously in an arbitrary number of input channels given by chanin (list)
    in file filerec. The number of seconds to record after the signal has faded out can be changed
    with the parameter revtime and the device can be changed if the default is not used
    '''
    
    if sdevice is not None:
        sd.default.device = sdevice
    if type(fplay) is str:
        fs2, data = wavfile.read(fplay + '.wav')
    elif type(fplay) is np.ndarray:
        if fplay.ndim > 1:
            data = fplay[:,0]
        else:    
            data = fplay
        fs2=fs        
    else:
        raise TypeError('Input must be ndarray or filename')     
    sd.default.samplerate = fs2
    nchanout = len(chanout)
    data = np.append(data,np.zeros(int(revtime*fs2))) # extends data for reverb
    data = np.repeat(data[:,np.newaxis],nchanout,1) # repeat the array
    # wait delay and print some message
    # loop over repeat
    rec = sd.playrec(data, input_mapping=chanin,output_mapping=chanout,dtype='float64') # records with 64 bits for processing
    sd.wait() # wait for recording to finish
    print('finished')
    if write_wav:
        wavfile.write(filerec + '.wav',fs2,rec.astype(np.float32)) 
    # end loop
    return rec

def play(fplay,chanout=[1],sdevice=None,normalized=False,fs=48000,block=False):
    '''
    function to play the array fplay (only the first channel) or mono file fplay.wav through the output channels chanout (list)
    The device can be changed if the default is not used. Block True blocks until the end of playback
    '''
    if sdevice is not None:
        sd.default.device = sdevice
    if type(fplay) is str:
        fs, data = wavfile.read(fplay + '.wav')
    elif type(fplay) is np.ndarray:
        if fplay.ndim > 1:
            data = fplay[:,0]
        else:    
            data = fplay     
    else:
        raise TypeError('Input must be ndarray or filename') 
    sd.default.samplerate = fs
    # nchanout = chanout[-1]+1
    mapping = [c for c in chanout]
    # data = np.repeat(data[:,np.newaxis],nchanout,1) # repeats the array 
    if normalized:
        sd.play(data/np.max(np.abs(data)), mapping=mapping,blocking=block) 
    else:
        sd.play(data, mapping=mapping,blocking=block)     
    return

def load_pcm(file,nchan,nbytes=4):
    """
    Function to load a raw PCM audio file with nchan channels and nbytes little endian
    """
    nmax = 2**(nbytes*8-1)
    data=np.memmap(file, dtype='u1', mode='r')
    nsamples=data.shape[0]//(nchan*nbytes)
    if nbytes==4:
        realdata=np.reshape(data.view(np.int32)/nmax,(nsamples,nchan)).astype('float64')
    elif nbytes==2:
        realdata=np.reshape(data.view(np.int16)/nmax,(nsamples,nchan)).astype('float32')
    elif nbytes==1:
        realdata=np.reshape(data.view(np.int8)/nmax,(nsamples,nchan)).astype('float32')
    else:
        raise Exception("Only 4,2 or 1 bytes allowed")
    return realdata

