from picamera2 import Picamera2
from PIL import Image
from websocket import create_connection
import time
import numpy as np
import json
import RPi.GPIO as GPIO
import threading
import queue

WIDTH = 320
HEIGHT= 256
FLOOR_THRESHOLD = .25
BUFFER_SIZE = 20
MAX_TICKS = 3000
TIMEOUT_MAX = 300 #fps

def sum_px_per_column(image):
	"""
	Takes a 2d array of a grey image and returns a 1d array of values
	"""
	column_sums = np.sum(image, axis=0).astype(np.int32)
	return column_sums

def add_graph_to_image(nparr, image, priority):
	for x in range(len(nparr)):
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
	for x in range(len(nparr)):
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

def handleMsg(q: queue.Queue):
	print("worker started")
	ws = create_connection("ws://localhost:8081")
	message = ""
	while True:
		message = ws.recv()
		if message == "gameEnd" or message == "gameStart":
			q.put_nowait(message)
	

def wait_for_start():
	while True:
		if not q.empty():
			wsMessage = q.get_nowait()
			if (wsMessage == "gameStart"):
				break;
		else:
			time.sleep(1)


#init cam
picam2 = Picamera2()
config = picam2.create_preview_configuration({'format':'YUV420', 'size': (WIDTH, HEIGHT)})
picam2.configure(config)
picam2.start()
print("camera init")

GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.OUT)
print("init gpio")

q = queue.Queue()
ws = create_connection("ws://localhost:8081")
t = threading.Thread(target=handleMsg, args=(q,))
t.start()

#init mask
with open("/home/math27182/Documents/windy/gray/mask.txt", 'r') as maskFile:
	maskCoords = json.load(maskFile)

while True:
	print("waiting")
	# wait for start condition
	wait_for_start()
	
	#set/reset values
	times = []
	lastSums = []
	sums = np.array([])
	diffs = np.array([])
	rollingAvg = np.array([])
	floor = 0
	peakPos = 0
	timeout = -1

	print("starting")
	GPIO.output(23, GPIO.HIGH)
	for i in range(MAX_TICKS):
		# check endgame condition
		if timeout == 0:
			ws.send(json.dumps([0,0]))
			print('exiting timeout')
			break
		if timeout < 200 and timeout%30:
			ws.send(json.dumps([0,0]))
		
		if not q.empty():
			wsMessage = q.get_nowait()
			if wsMessage == "gameEnd":
				print('exiting ws')
				break

		startTime = time.time()
		yuv = picam2.capture_array()
		grey = yuv[maskCoords[1]:maskCoords[3], maskCoords[0]:maskCoords[2]]
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
			#put graph on the buttom of the image
			biggerPic = grey
			if maskCoords[3] - maskCoords[1] < 256:
				extraPixels = np.zeros((256, maskCoords[2] - maskCoords[0]), dtype=np.uint8)
				biggerPic = np.concatenate((grey, extraPixels), axis=0)
			
			#print sums
			add_graph_to_image(sums, biggerPic, 0)
			add_graph_to_image(rollingAvg, biggerPic, 1)
			add_graph_to_image(diffs, biggerPic, 2)
			if peakPos > 0:
				biggerPic[:HEIGHT, peakPos] = 255
			biggerPic[HEIGHT-int(floor/255), :WIDTH] = 255

			#save image from array
			im2 = Image.fromarray(biggerPic)
			im2.save(f"/home/math27182/Documents/windy/windygame/temp/maxima{i}.jpg")

	GPIO.output(23, GPIO.LOW)
	#print timing stats
	times_np = np.array(times)
	print(f"[{np.min(times_np): .0f}ms, {np.max(times_np): .0f}ms, {np.mean(times_np): .0f}ms]")


