#!/usr/bin/python
import pifacecad
import socket
import time, datetime
import RPi.GPIO as GPIO
import urllib.request, json
import csv
import subprocess
from urllib.error import URLError, HTTPError

def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]

cad=pifacecad.PiFaceCAD()
cad.lcd.backlight_on()
cad.lcd.cursor_off() 
cad.lcd.write (get_ip_address())  # should print "192.168.100.37"

GPIO.setmode (GPIO.BCM)
GPIO.setup(24, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(25, GPIO.IN, pull_up_down=GPIO.PUD_UP)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('localhost',8888))

dateString = '%d/%m/%y %H%M:%S'
oldtime=time.time()
oldmin=time.time()
oldday=99
oldmin=999
row=[]

while 1:
	#update the display every second
	cad.lcd.set_cursor(0, 1)
	cad.lcd.write(datetime.datetime.now().strftime(dateString))
	cad.lcd.set_cursor(14, 0)
	if (GPIO.input(24)!=0): 
		cad.lcd.write("O") #this was intended to monitor the 2-port valve status
	else:
		cad.lcd.write("I")
	if (GPIO.input(25)!=0): 
		cad.lcd.write("O")
	else:
		cad.lcd.write("I")
		
	#log heating values every 10s if changed
	if time.time() - oldtime > 9:
		oldtime=time.time()
		urlData = "http://192.168.1.240:8080/data"
		try:
			webURL = urllib.request.urlopen(urlData)
		except HTTPError as e:
			print('The server couldn\'t fulfill the request.')
			print('Error code: ', e.code)
		except URLError as e:
			print('We failed to reach a server.')
			print('Reason: ', e.reason)
		else:
			data = webURL.read()
			encoding = webURL.info().get_content_charset('utf-8')
			JSON_object = json.loads(data.decode(encoding))
			tr=datetime.datetime.now().hour + datetime.datetime.now().minute/60 + datetime.datetime.now().second/3600
			try:
				hwtemp=(JSON_object['v65']['messages']['State']['fields']['temp']['value'])
				valvestate=(JSON_object['v65']['messages']['State']['fields']['state']['value'])
				flowtemp=(JSON_object['bai']['messages']['Status01']['fields']['0']['value'])
				returntemp=(JSON_object['bai']['messages']['Status01']['fields']['1']['value'])
				active=(JSON_object['bai']['messages']['Status01']['fields']['5']['value'])
				flowtempdesired=(JSON_object['bai']['messages']['SetMode']['fields']['flowtempdesired']['value'])
				displayedroomtemp=(JSON_object['350']['messages']['DisplayedRoomTemp']['fields']['temp']['value'])
			except:
				print('JSON decode error.')
				print(data)
			else:
				if valvestate=="heat": nvalvestate=25
				elif valvestate=="water": nvalvestate=15
				else: nvalvestate=20
				nactive=0
				if (active=="off"): nactive=0
				elif (active=="on"): nactive=5
				else: nactive=10
				newrow = [tr, nactive, flowtemp, returntemp, flowtempdesired, hwtemp, nvalvestate,displayedroomtemp]
				if newrow[1: ]!=row[1: ]: #compare lists from 2nd element onwards, ignoring the time - only store if different
					row=newrow
					print (row)  #debug
					
					if oldday!=datetime.datetime.now().weekday():  #if the day has changed, write new file or erase old file
						oldday=datetime.datetime.now().weekday()
						if datetime.datetime.now().hour==0: #only if the hour is 0, if we restart then don't erase
							ofile=open('/var/ebusd/html/day' + str(oldday) + '.csv', 'w')
							ofile.close()

					with open('/var/ebusd/html/day' + str(oldday) + '.csv', 'a') as csvFile:
						writer = csv.writer(csvFile)
						writer.writerow(row)

					csvFile.close()
		
	#read roomtemp every 5min
	if time.time() - oldmin > 5*60:
		oldmin=time.time()
		print('Send roomtemp request:')
		message = 'read DisplayedRoomTemp \r\n' 
		sock.sendall(message.encode('utf-8'))

		message = 'read WaterPressure \r\n' 
		sock.sendall(message.encode('utf-8'))

		#urlData = "http://192.168.1.240:8080/data/350/displayedroomtemp?exact=true&maxage=0"
		#try:
		#	webURL = urllib.request.urlopen(urlData)
		#except HTTPError as e:
		#	print('The server couldn\'t fulfill the request.')
		#	print('Error code: ', e.code)
		#except URLError as e:
		#	print('We failed to reach a server.')
		#	print('Reason: ', e.reason)
		#else:
		#	print(webURL.read())
		#proc = subprocess.Popen(['ebusctl','read','DisplayedRoomTemp'], shell=True,
        #     stdin=None, stdout=None, stderr=None, close_fds=True)
		


	if (cad.switches[4].value!=0): 
		break  #quit python if menu button pressed
	time.sleep(1)
	
	
	
cad.lcd.clear()
cad.lcd.write ("End")	
