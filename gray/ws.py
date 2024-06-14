from picamera2 import Picamera2
from PIL import Image
from websocket import create_connection
import time
import numpy as np
import json
import RPi.GPIO as GPIO

WIDTH = 320
HEIGHT= 256
FLOOR_THRESHOLD = .25
BUFFER_SIZE = 20
MAX_TICKS = 3000
TIMEOUT_MAX = 30 #fps

def sum_px_per_column(image):
	"""
	Takes a 2d array of a grey image and returns a 1d array of values
	"""
	column_sums = np.sum(image, axis=0).astype(np.int32)
	return column_sums

def add_graph_to_image(nparr, image, priority):
	for x in range(WIDTH):
		y = int(nparr[x] / HEIGHT)
		image[HEIGHT - max(y, 1), x] = 0 + priority*15 if y > 128 else 255 - priority*15
	
def column_sums_difference(current_sum, previous_sum, n):
	#for x in range(WIDTH):
	#	print(f"{x} {current_sum[x]} {previous_sum[x]} {abs(current_sum[x] - previous_sum[x])}")
	return np.abs(current_sum - previous_sum)

def average_of_last_sums(lastSums):
    return np.mean(np.vstack(lastSums), axis=0)
	
def integrate_peaks(nparr, floor):
	lastY = 0
	peaks = []
	extents = []
	peak = 0
	localMax = 0
	localMaxPos = 0
	for x in range(WIDTH):
		y = nparr[x]-floor
		if y > 0:
			# if peak == 0:
				# start peak if y > 0 and peak == 0
			if y > localMax:
				localMax = y
				localMaxPos = x
			peak+=y
		elif peak != 0:
				# close peak if y = 0 and peak > 0
				extents.append(localMaxPos)
				peaks.append(peak)
				peak = 0
				localMax = 0
	if peak > 0: 
		peaks.append(int(peak))
	if (len(peaks) > 0):
		i = peaks.index(max(peaks))
		if (i >= 0 and len(extents) > i):
			return [extents[i], int(sum(peaks))]
	return []

picam2 = Picamera2()
config = picam2.create_preview_configuration({'format':'YUV420', 'size': (WIDTH, HEIGHT)})
picam2.configure(config)
picam2.start()
print("start")

GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.OUT)
GPIO.output(23, GPIO.HIGH)

times = []
lastSums = []
sums = np.array([])
diffs = np.array([])
rollingAvg = np.array([])
floor = 0
peakPos = 0
timeout = -1


ws = create_connection("ws://localhost:8081")

for i in range(MAX_TICKS):
	# check endgame condition
	if timeout == 0:
		ws.send(json.dumps([0,0]))
		print('exiting')
		break
	if timeout < 20 and timeout%4:
		ws.send(json.dumps([0,0]))
	
	#recvData = ws.recv_nowait()
	#if (len(recvData)):
	#	print(recvData)

	print(i)
	startTime = time.time()
	yuv = picam2.capture_array()
	grey = yuv[:HEIGHT, :WIDTH]
	sums = sum_px_per_column(grey)
	if (len(lastSums) >= BUFFER_SIZE):
		#compute diff
		rollingAvg = average_of_last_sums(lastSums[:10])
		diffs = column_sums_difference(sums, rollingAvg, i)
		#compute peak
		floor = max(int(diffs.max() * FLOOR_THRESHOLD), 2*HEIGHT)
		peakData = integrate_peaks(diffs, floor)
		if len(peakData) == 2:
			ws.send(json.dumps(peakData))
			peakPos = peakData[0];
			timeout = TIMEOUT_MAX
		else:
			peakPos = 0;
			if timeout > 0: 
				timeout-=1
		
		lastSums.pop(0)
	lastSums.append(sums)
	#timing stats
	times.append(round((time.time() - startTime)*1000))
	
	#every 10 ticks, save a diagnostic photo to the server dir
	if i > BUFFER_SIZE and i % 12 ==0:
		#print sums
		add_graph_to_image(sums, grey, 0)
		add_graph_to_image(rollingAvg, grey, 1)
		add_graph_to_image(diffs, grey, 2)
		if peakPos > 0:
			grey[:HEIGHT, peakPos] = 255
		grey[HEIGHT-int(floor/255), :WIDTH] = 255

		#save image from array
		im2 = Image.fromarray(grey)
		im2.save(f"/home/math27182/Documents/windy/windygame/temp/maxima{i}.jpg")

GPIO.output(23, GPIO.LOW)
#print timing stats
times_np = np.array(times)
print(f"[{np.min(times_np): .0f}ms, {np.max(times_np): .0f}ms, {np.mean(times_np): .0f}ms]")


