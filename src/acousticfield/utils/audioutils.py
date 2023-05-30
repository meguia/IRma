import sounddevice as sd
import numpy as np

def list_devices():
    devices =  sd.query_devices()
    inputs = [d['name'] for d in devices if d['max_input_channels'] > 0]
    outputs = [d['name'] for d in devices if d['max_output_channels'] > 0]
    return inputs, outputs

def get_device_number(device_name):
    return  sd.query_devices(device_name)['index']

def get_device_name(device_number):
    return  sd.query_devices(device_number)['name']

def get_default_samplerate(device_name):
    return sd.query_devices(device_name)['default_samplerate']

def assign_device(input_device, output_device,sample_rate): 
    sd.default.device = [get_device_number(input_device), get_device_number(output_device)]
    sd.default.samplerate = get_default_samplerate(output_device)
    output_name = output_device
    input_name = input_device
    print("Usando salida de audio: " + output_name)
    print("Usando entrada de audio: " + input_name)

def get_max_channels(input_device, output_device):
    max_chanin = sd.query_devices(input_device)['max_input_channels']
    max_chanout = sd.query_devices(output_device)['max_output_channels']
    return max_chanin, max_chanout

def test_output(output_device,sample_rate):
    sd.default.device = output_device
    sd.default.samplerate = sample_rate
    duration = 1.5  # seconds
    t = np.arange(int(sample_rate * duration)) / sample_rate
    x = np.sin(2 * np.pi * 440 * t)
    sd.play(x, sample_rate)
    sd.wait(duration)
    return 

def test_input(input_device,sample_rate):
    sd.default.device = input_device
    sd.default.samplerate = sample_rate
    duration = 1.5  # seconds
    myrecording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1)
    sd.wait()
    return myrecording   
