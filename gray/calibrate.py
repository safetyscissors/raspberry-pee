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
def sum_px_per_column(image):
	"""
	Takes a 2d array of a grey image and returns a 1d array of values
	"""
	column_sums = np.sum(image, axis=0).astype(np.int32)
	return column_sums

def add_graph_to_image(nparr, image):
	for x in range(WIDTH):
		y = int(nparr[x] / HEIGHT)
		image[HEIGHT - max(y, 1), x] = 0 if y > 128 else 255
	
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

GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.OUT)
GPIO.output(23, GPIO.HIGH)

picam2 = Picamera2()
config = picam2.create_preview_configuration({'format':'YUV420', 'size': (WIDTH, HEIGHT)})
picam2.configure(config)
picam2.start()
print("calibrate.py start")

times = []
lastSums = []
sums = np.array([])
diffs = np.array([])
rollingAvg = np.array([])
floor = 0
peakPos = 0

for i in range(3):
	yuv = picam2.capture_array()
	grey = yuv[:HEIGHT, :WIDTH]
	sums = sum_px_per_column(grey)
	lastSums.append(sums)
	
rollingAvg = average_of_last_sums(lastSums)

GPIO.output(23, GPIO.LOW)
#save rolling avg as calibration 
np.savetxt("calibration.txt", rollingAvg)

#save image from array
add_graph_to_image(rollingAvg, grey)
im2 = Image.fromarray(grey)
im2.save(f"../windygame/temp/calibrate.jpg")

