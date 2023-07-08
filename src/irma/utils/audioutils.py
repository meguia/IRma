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
    if device_number < 0 :
        device_number = 0
    return  sd.query_devices(device_number)['name']

def get_device_number_name(device_number):
    if device_number < 0 :
        device_number = 0
    return  ",".join([str(device_number), sd.query_devices(device_number)['name']])

def get_default_samplerate(device_name):
    return sd.query_devices(device_name)['default_samplerate']

def assign_device(input_device, output_device,sample_rate): 
    input_device_number=get_device_number(input_device)
    output_device_number=get_device_number(output_device)
    sd.default.device = [input_device_number, output_device_number]
    sd.default.samplerate = sample_rate
    print("Usando salida de audio: " + output_device)
    print("Usando entrada de audio: " + input_device)
    print("Sampling Rate: " + str(sd.default.samplerate))  

def get_max_channels(input_device, output_device):
    input_device_number=get_device_number(input_device)
    output_device_number=get_device_number(output_device)
    max_chanin = sd.query_devices(input_device_number)['max_input_channels']
    max_chanout = sd.query_devices(output_device_number)['max_output_channels']
    return max_chanin, max_chanout

def test_output(input_device,output_device,sample_rate):
    assign_device(input_device, output_device,sample_rate)
    duration = 1.5  # seconds
    t = np.arange(int(sample_rate * duration)) / sample_rate
    x = np.sin(2 * np.pi * 440 * t)
    sd.play(x, sample_rate)
    sd.wait(duration)
    return 

def test_input_tic(input_device,output_device,sample_rate,dur=0.3):
    assign_device(input_device, output_device,sample_rate)
    return sd.rec(int(dur * sample_rate), samplerate=sample_rate, channels=1,blocking=True)
