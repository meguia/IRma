import sounddevice as sd
import numpy as np

def list_devices():
    devices =  sd.query_devices()
    inputs = []
    outputs = []
    for n,d in enumerate(devices):
        if d['max_input_channels'] > 0:
            inputs.append(f"{n},{d['name']}")
        if d['max_output_channels'] > 0:
            outputs.append(f"{n},{d['name']}")        
    return inputs, outputs

def get_device_number(device):
    return  int(device.split(",")[0])

def get_device_name(device_number):
    return  sd.query_devices(device_number)['name']

def get_device_number_name(device_number):
    return  ",".join([str(device_number), sd.query_devices(device_number)['name']])

def get_default_samplerate(device_name):
    return sd.query_devices(device_name)['default_samplerate']

def assign_device(input_device, output_device,sample_rate): 
    input_device_number=get_device_number(input_device)
    output_device_number=get_device_number(output_device)
    sd.default.device = [input_device_number, output_device_number]
    sd.default.samplerate = sample_rate
    print("Using audio output: " + output_device)
    print("Using audio input: " + input_device)
    print("Sampling Rate: " + str(sd.default.samplerate))  

def get_max_channels(input_device, output_device):
    input_device_number=get_device_number(input_device)
    output_device_number=get_device_number(output_device)
    max_chanin = sd.query_devices(input_device_number)['max_input_channels']
    max_chanout = sd.query_devices(output_device_number)['max_output_channels']
    return max_chanin, max_chanout

import numpy as np
import sounddevice as sd

def test_output_tic(input_device, output_device, sample_rate, stop_event=None,
                    freq=440.0, duration=1.5, blocksize=1024):
    assign_device(input_device, output_device, sample_rate)
    if stop_event is None:
        class _Dummy:
            def is_set(self): return False
        stop_event = _Dummy()
    n_total = int(round(sample_rate * duration))
    phase = 0.0
    phase_inc = 2.0 * np.pi * freq / sample_rate
    written = 0
   
    with sd.OutputStream(samplerate=sample_rate, channels=1, dtype="float32",
                         blocksize=blocksize) as stream:
        while written < n_total and not stop_event.is_set():
            n = min(blocksize, n_total - written)
            idx = np.arange(n, dtype=np.float64)
            y = np.sin(phase + phase_inc * idx).astype(np.float32)
            phase += phase_inc * n
            stream.write(y.reshape(-1, 1))
            written += n
    if stop_event.is_set():
        try:
            sd.stop()
        except Exception:
            pass


def test_input_tic(input_device, output_device, sample_rate, dur=0.3,
                   stop_event=None, blocksize=1024):
    assign_device(input_device, output_device, sample_rate)
    if stop_event is None:
        class _Dummy:
            def is_set(self): return False
        stop_event = _Dummy()
    n_total = int(round(dur * sample_rate))
    blocks = []
    read_total = 0

    with sd.InputStream(samplerate=sample_rate, channels=1, dtype="float32",
                        blocksize=blocksize) as stream:
        while read_total < n_total and not stop_event.is_set():
            n = min(blocksize, n_total - read_total)
            x, overflowed = stream.read(n)   # x shape: (n, 1)
            blocks.append(x.copy())
            read_total += n
            
    if not blocks:
        return np.zeros((0, 1), dtype=np.float32)
    return np.vstack(blocks)
