import numpy as np
import sounddevice as sd
import pandas as pd
from scipy import signal
from scipy.io import wavfile
from scipy.stats import linregress
from matplotlib import pyplot as plt
from IPython.display import display, HTML

def sweep(T, f1=30, f2=22000,filename=None,fs=48000,fade=0.02,order=2):
    '''
    Genera un sweep exponencial de duracion T con frecuencia de sampleo fs desde la frecuencia f1
    hasta f2, lo almacena en filename.wav y guarda el filtro inverso en filename_inv.npy
    como parametros opcionales se pueden modificar el fadein y fadeout de la senal con fade
    usa el metodo de Muller and Massarani, "Transfer Function Measurement with Sweeps" 
    que era el implementado en Matlab. El unico cambio es que puede elegirse el orden del filtro
    '''
    if filename is None:
        filename = 'sweep' + str(T) + 's_' + str(f1) + '_' + str(f2)   
    N = int(T*fs)
    Gd_start = int(np.ceil(min(N/10,max(fs/f1, N/200)))) # inicio del group delay fs/f1 acotado entre N/10 y N/200
    postfade = int(np.ceil(min(N/10,max(fs/f2,N/200)))) # fadeout 
    Nsweep = N - Gd_start - postfade
    tsweep = Nsweep/fs
    # filtros pasabanda para crear la respuesta en frecuencia deseada
    if (f2 < fs/2):
        B2, A2 = signal.butter(order,f2/(fs/2)) # lowpass
        B1, A1 = signal.butter(order,f1/(fs/2),'highpass') # higpass
    else:
        B2 = [1,2,1]
        A2 = B2
        B1, A1 = signal.butter(2,f1/(fs/2),'highpass' ) # order 2
    W1, H1 = signal.freqz(B1,A1,N+1,fs=fs)
    W2, H2 = signal.freqz(B2,A2,N+1,fs=fs)   
    # espectro rosa (-10dB por decada, or 1/(sqrt(f)) 
    mag = np.sqrt(f1/W1[1:])
    mag = np.insert(mag,0,mag[0]) # completamos f=0
    mag = mag*np.abs(H1)*np.abs(H2) # y aplicamos pasabanda\
    Gd = tsweep * np.cumsum(mag**2)/np.sum(mag**2) # calculo del group delay
    Gd = Gd + Gd_start/fs # agrega el predelay
    Gd = Gd*fs/2;   # convierte a samples
    ph = -2.0*np.pi*np.cumsum(Gd)/(N+1) # obtiene la fase integrando el GD
    ph = ph - (W1/(fs/2))*np.mod(ph[-1],2.0*np.pi) # fuerza la fase a terminar en multiplo de 2 pi
    cplx = mag*np.exp(1.0j*ph) # arma el espectro del sweep a partir de la magnitud y la fase
    cplx = np.append(cplx,np.conj(cplx[-2:0:-1])) # completa el espectro con f negativas para sweep real
    sweep = np.real(np.fft.ifft(cplx)) # Y aca esta el sweep finalmente
    sweep = sweep[:N] # recorta a la cantidad de samples original
    w = signal.hann(2*Gd_start) # ventana para fadein
    sweep[:Gd_start] = sweep[:Gd_start]*w[:Gd_start]
    w = signal.hann(2*postfade) # ventana para fadeout
    sweep[-postfade:] = sweep[-postfade:]*w[-postfade:]
    sweep = sweep/max(np.abs(sweep)) # normaliza
    # Calculo del filtro inverso
    sweepfft = np.fft.fft(sweep)
    invsweepfft = 1.0/sweepfft
    #  para evitar divergencias re aplicamos el pasabanda
    W1, H1 = signal.freqz(B1,A1,N,whole=True,fs=fs)
    W2, H2 = signal.freqz(B2,A2,N,whole=True,fs=fs)
    invsweepfftmag  = np.abs(invsweepfft)*np.abs(H1)*np.abs(H2)
    invsweepfftphase = np.angle(invsweepfft)
    invsweepfft = invsweepfftmag*np.exp(1.0j*invsweepfftphase) # resintesis
    np.save(filename + '_inv',invsweepfft) # guarda el filtro inverso en formato npy
    wavfile.write(filename + '.wav',fs,sweep) # guarda el sweep en wav con formato float 32 bits
    return sweep

def noise(T, color='white', filename=None, fin=50, fout=50, fs=48000):

def pinknoise(nrows, ncols=16):
    """
    Genera ruido rosa usando el algoritmpo de Voss-McCartney, tomado de
    https://github.com/AllenDowney/ThinkDSP/blob/master/code/voss.ipynb
    nrows: numero de samples a generar
    rcols: nomero de fuente indeptes
    """
    array = np.empty((nrows, ncols))
    array.fill(np.nan)
    array[0, :] = np.random.random(ncols)
    array[:, 0] = np.random.random(nrows)
    n = nrows
    cols = np.random.geometric(0.5, n)
    cols[cols >= ncols] = 0
    rows = np.random.randint(nrows, size=n)
    array[rows, cols] = np.random.random(n)
    df = pd.DataFrame(array)
    df.fillna(method='ffill', axis=0, inplace=True)
    total = df.sum(axis=1)
    return total.values    

def mls(T, filename=None, fs=48000):
    
    