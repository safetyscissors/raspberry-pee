from picamera2 import Picamera2
from PIL import Image
import time
import numpy as np

WIDTH = 320
HEIGHT= 240

def sum_px_per_column(image):
	"""
	Takes a 2d array of a grey image and returns a 1d array of values
	"""
	column_sums = np.sum(image, axis=0)
	return column_sums

def add_graph_to_image(sums, image):
	for x in range(WIDTH):
		y = int(sums[x] / HEIGHT)
		image[HEIGHT - y, x] = 0 if y > 128 else 255
	

picam2 = Picamera2()
config = picam2.create_preview_configuration({'format':'YUV420', 'size': (WIDTH, HEIGHT)})
picam2.configure(config)
picam2.start()
print("start")
times = []
sums = np.array([])

for i in range(0,3):
	startTime = time.time()
	yuv = picam2.capture_array()
	grey = yuv[:HEIGHT, :WIDTH]
	sums = sum_px_per_column(grey)
	#timing stats
	times.append(round((time.time() - startTime)*1000))

#print timing stats
times_np = np.array(times)
print(f"[{np.min(times_np): .0f}ms, {np.max(times_np): .0f}ms, {np.mean(times_np): .0f}ms]")

#print sums
add_graph_to_image(sums, grey)

#save image from array
im2 = Image.fromarray(grey)
im2.save("sum.jpg")
