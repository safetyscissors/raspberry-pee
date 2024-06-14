from picamera2 import Picamera2
from PIL import Image
import time
import numpy as np

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
			print(f"x: {extents[i]}, v: {int(sum(peaks))}")
			return extents[i]
	return 0
		
picam2 = Picamera2()
config = picam2.create_preview_configuration({'format':'YUV420', 'size': (WIDTH, HEIGHT)})
picam2.configure(config)
picam2.start()
print("start")

times = []
lastSums = []
sums = np.array([])
diffs = np.array([])
rollingAvg = np.array([])
floor = 0
peakPos = 0

for i in range(150):
	startTime = time.time()
	yuv = picam2.capture_array()
	grey = yuv[:HEIGHT, :WIDTH]
	sums = sum_px_per_column(grey)
	if (len(lastSums) >= 10):
		#compute diff
		rollingAvg = average_of_last_sums(lastSums)
		diffs = column_sums_difference(sums, rollingAvg, i)
		#compute peak
		floor = max(int(diffs.max() * FLOOR_THRESHOLD), 2*HEIGHT)
		peakPos = integrate_peaks(diffs, floor)
		
		lastSums.pop(0)
	lastSums.append(sums)
	#timing stats
	times.append(round((time.time() - startTime)*1000))
	
	if i > 10 and i % 12 ==0:
		#print sums
		add_graph_to_image(sums, grey)
		add_graph_to_image(rollingAvg, grey)
		add_graph_to_image(diffs, grey)
		grey[:HEIGHT, peakPos] = 255
		grey[HEIGHT-int(floor/255), :WIDTH] = 255

		#save image from array
		im2 = Image.fromarray(grey)
		im2.save("../windygame/maxima.jpg")

#print timing stats
times_np = np.array(times)
print(f"[{np.min(times_np): .0f}ms, {np.max(times_np): .0f}ms, {np.mean(times_np): .0f}ms]")


