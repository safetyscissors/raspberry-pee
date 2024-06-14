from picamera2 import Picamera2
from PIL import Image
import time
import numpy as np

picam2 = Picamera2()
WIDTH = 320
HEIGHT= 240
config = picam2.create_preview_configuration({'format':'YUV420', 'size': (WIDTH, HEIGHT)})
picam2.configure(config)
picam2.start()
print("start")
times = []

for i in range(0,3):
	startTime = time.time()
	yuv = picam2.capture_array()
	grey = yuv[:HEIGHT, :WIDTH]
	grey[0, :100] = 0
	grey[:50, 0] = 0
	#timing stats
	times.append(round((time.time() - startTime)*1000))

#print timing stats
times_np = np.array(times)
print(f"[{np.min(times_np): .0f}ms, {np.max(times_np): .0f}ms, {np.mean(times_np): .0f}ms]")

#save image from array
im = Image.fromarray(grey)
im.save("test_grey_zero_index.jpg")
