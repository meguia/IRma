#!/usr/bin/python3
import os
import serial
import time
import yaml

#Enable Serial Communication
port = serial.Serial('/dev/ttyUSB0', 
					baudrate=115200, 
					bytesize=8, 
					parity='N',
					stopbits=1, 
					timeout=1)

with open('/home/pi/acoustic_field/config/defaults.yaml') as file:
	opt = yaml.load(file, Loader=yaml.FullLoader)

def wrPort(command, nread=100, sleep=0.5):	
	port.write(str.encode(command+'\r\n'))
	time.sleep(0.5)
	port.flush()
	time.sleep(sleep)
	#Espera a que devuelva algo el módulo y lee (depende de la función)
	#Leo 100 bytes más del largo del mensaje original (quizás es medio exagerado que sean 100)
	rcv = port.read(len(command)+nread)
	time.sleep(0.5)
	port.flush()
	rcv= rcv.decode('utf-8')
	print(rcv)
	return rcv

def isOn():
	AT = wrPort('AT')
	wrPort('AT+CFUN=1')
	wrPort('AT+CGATT=1')
	return 'OK' in AT

def checkSignal():
	AT = wrPort('AT+CREG?')
	return '0,1' in AT

def connectAPN(APN):
	wrPort('AT+SAPBR=3,1,"APN",'+APN)
	AT = wrPort('AT+SAPBR=1,1')	
	return 'OK' in AT

def checkIP():
	AT = wrPort('AT+SAPBR=2,1')
	return '"0.0.0.0"' not in AT	

def initHTTP():
	wrPort('AT+HTTPINIT')
	wrPort('AT+HTTPPARA="CID",1')
	wrPort('AT+HTTPPARA="REDIR",0')
	wrPort('AT+HTTPSSL=1')
	return 'HTTP config OK'

def termHTTP():
	wrPort('AT+HTTPTERM')
	return 'HTTP service terminated'

def sendData(url, data):
	#saqué el último caracter de "data" porque era un salto de linea y daba problemas. CHEQUEAR
	wrPort('AT+HTTPPARA="URL","'+url+data[:-1]+'"')
	time.sleep(1)
	AT = wrPort('AT+HTTPACTION=0', sleep=10)
	upload = '0,302' in AT
	return upload, AT


def uploadQueue(url, queue, offset):
	file=open(queue, mode='r+')
	file.seek(offset)
	line = file.readline()
	#Hecho con while porque con for me daba problemas la funcion "next()" de tell()
	while line:
		upload, AT = sendData(url, line)
		print(f'upload: {upload}')
		print('Esto guardé en AT:\n'+AT, 'Fin de AT')
		if upload:
			offset=file.tell()
		else:
			file.close()
			return offset, upload
		line = file.readline()
	file.close()
	#if upload correcly -> upload=True
	return offset, upload

def restartModule():
	wrPort('AT+CFUN=1,1')
	print('Restarting Module')
	time.sleep(5)

def disconnect():
	wrPort('AT+SAPBR=0,1')

def shutDown():
	wrPort('AT+CPOWD=1')

def main():
	cont = 0
	offset = opt['offset']
	APN = opt['APN']
	URL = opt['URL']
	queue = opt['queue']
	inicio = datetime.now()
	#chequear que no este corriendo otro gsm_send
	while (datetime.now() - inicio) < opt['timeout']:

		if isOn():
			if checkSignal():	#if 0,1 -> True
				if connectAPN(APN) or checkIP():
					initHTTP()
					while checkIP():
						offset,success = uploadQueue(URL, queue, offset)
						opt['offset'] = offset
						time.sleep(5)
				else:
					print('I have signal but can\'t connect to Internet')

			else:
				print('No signal. Reconnecting')
				time.sleep(1)

			if cont==10:
				restartModule()

			cont += 1
		else:
			raise AssertionError('No response from Module')

	with open('/home/pi/options.yaml', 'w') as file:	    
	    yaml.dump(opt,file)

if __name__ == "__main__":
	try:
		main()
	except AssertionError as e:
		raise
	except KeyboardInterrupt:
		time.sleep(2)
		wrPort('AT')
		termHTTP()
		#disconnect()
		#shutDown()