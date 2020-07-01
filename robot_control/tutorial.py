'''
This is a compilation of examples ran in the jupyter notebook during the tutorial session, for both Robomaster and Tello.
'''

# 1. Initializing

from EP_api import Robot, findrobotIP
import time

robot = Robot('192.168.2.1') # WIFI direct
robot = Robot('192.168.42.2') # USB
robot = Robot(findrobotIP()) # router

# 2. example commands
# a.
robot.move('x 1 y 0.5')
time.sleep(2)
robot._sendcommand('chassis move x -1 y -0.5;') # use _sendcommand and refer to SDK for format
time.sleep(2)

robot.rotate('-90') # CCW 90degrees
time.sleep(2)

robot.forward('-0.5') # constantly move backwards at 0.5m/s
time.sleep(2)

robot.right('-0.5') # constantly move left at 0.5m/s
time.sleep(2)

robot.stop()

# b. gimbal commands
robot.rotategimbal('p 10 y 90') # displacement
robot.rotategimbalto('p 10 y 90') # absolute end position
robot.center()

# c. arm commands
robot.movearm('x 10 y 10')
robot.center()
robot.openarm()
robot.closearm()

robot.exit() # this includes stop and center


# 3. Video stream
# !pip install opencv-python
import cv2
import time

robot.startvideo()

while robot.frame is None: # this is for video warm up. when frame is received, this loop is exited.
	pass


while True:
	cv2.namedWindow('Live video', cv2.WINDOW_NORMAL)
	cv2.imshow('Live video', robot.frame) # access the video feed by robot.frame

	k = cv2.waitKey(16) & 0xFF
	if k == 27: # press esc to stop
		print("Quitting")
		robot.exit()
		break


## TELLO
# 1. Initializing

from Tello_api import Tello
import time
tello = Tello()


# # 2. Basic commands

tello._sendcommand('takeoff')
tello.start_pad_det() # enables mission pad detection
time.sleep(5)
tello._sendcommand('jump 100 0 100 60 0 m1 m2')

tello.exit() # this includes land


# 3. Video stream and keyboard movements
# !pip install opencv-python
import cv2
import time

tello.startvideo()
tello.startstates() # to read height of tello

while tello.frame is None: # this is for video warm up. when frame is received, this loop is exited.
	pass
while True:
	cv2.namedWindow('Tello video', cv2.WINDOW_NORMAL)
	cv2.imshow('Tello video', cv2.flip(tello.frame, 0)) # flip required if using mirror

	k = cv2.waitKey(16) & 0xFF
	if k == 27: # press esc to stop
		tello.exit()
		break

	elif k != -1: # press wasdqe to control tello. u,j to control height. t,l to takeoff and land
		tello.act(k) 
