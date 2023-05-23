import numpy as np
import sounddevice as sd
from scipy.io import wavfile

def time_rec(filerec,duration,delay=0,chanin=[1],fs=48000,sdevice=None,write_wav=True):
    '''
    funcion grabar durante dur segundos en una cantidad arbitraria de canales de entrada dada por chanin (lista)
    en archivo filerec. 
    '''
    #agregar una alerta de clipeo y la opcion de correr dummy
    if sdevice is not None:
        sd.default.device = sdevice
    sd.default.samplerate = fs
    nchanin = chanin[-1]
    # loop sobre repeat
    rec = sd.rec(int(duration*fs),samplerate=fs,channels=nchanin,dtype='float64') # graba con 64 bits para proceso
    sd.wait() # espera que termine la grabacion
    print('finished')
    rec = rec[:,chanin-1]
    if write_wav:
        wavfile.write(filerec + '.wav',fs,rec) # guarda el array grabado en wav con 32 bits
    # fin loop   
    return rec

def play_rec(fplay,filerec,delay=0,chanout=[1],chanin=[1],revtime=2.0,sdevice=None,write_wav=True,fs=48000):
    '''
    funcion para reproducir el archivo mono wav fileplay a traves de los canales de salida chanout (lista)
    y grabarlo simultaneamente en una cantidad arbitraria de canales de entrada dada por chanin (lista)
    en archivo filerec. Puede cambiarse la cantidad de segundos que graba luego de que se extinguio 
    la senal revtime y cambiar el device si no se usa el default 
    '''
    #agregar una alerta de clipeo y la opcion de correr dummy
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
    nchanin = chanin[-1]
    nchanout = chanout[-1]
    data = np.append(data,np.zeros(int(revtime*fs))) # extiende data para agregar la reverberacion
    data = np.repeat(data[:,np.newaxis],nchanout,1) # repite el array 
    # wait delay e imprimir algun algun mensaje
    # loop sobre repeat
    rec = sd.playrec(data, channels=nchanin,dtype='float64') # graba con 64 bits para proceso
    sd.wait() # espera que termine la grabacion
    print('finished')
    rec = rec[:,chanin-1]
    if write_wav:
        wavfile.write(filerec + '.wav',fs,rec) # guarda el array grabado en wav con 32 bits
    # fin loop   
    return rec

def play(fplay,chanout=[1],sdevice=None,normalized=False,fs=48000,block=False):
    '''
    funcion para reproducir el array fplay (solo el primer canal) o archivo mono fplay.wav a traves de los canales de salida chanout (lista)
    Puede cambiar el device si no se usa el default. Block True bloquea hasta el fin de la reprocduccion
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
    # data = np.repeat(data[:,np.newaxis],nchanout,1) # repite el array 
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

