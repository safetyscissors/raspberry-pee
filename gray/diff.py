from picamera2 import Picamera2
from PIL import Image
import time
import numpy as np

WIDTH = 320
HEIGHT= 256

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

for i in range(15):
	startTime = time.time()
	yuv = picam2.capture_array()
	grey = yuv[:HEIGHT, :WIDTH]
	sums = sum_px_per_column(grey)
	if (len(lastSums) >= 10):
		print(f"diffing {i}")
		rollingAvg = average_of_last_sums(lastSums)
		diffs = column_sums_difference(sums, rollingAvg, i)
		lastSums.pop(0)
	else:
		print(f"skipping diff {i} {len(lastSums)}")
	
	lastSums.append(sums)
	#timing stats
	times.append(round((time.time() - startTime)*1000))
	


#print timing stats
times_np = np.array(times)
print(f"[{np.min(times_np): .0f}ms, {np.max(times_np): .0f}ms, {np.mean(times_np): .0f}ms]")

#print sums
add_graph_to_image(sums, grey)
add_graph_to_image(rollingAvg, grey)
add_graph_to_image(diffs, grey)
print(f"total delta: {np.sum(diffs)}")

#save image from array
im2 = Image.fromarray(grey)
im2.save("diff.jpg")
