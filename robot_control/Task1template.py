'''
This is an example script for solving task 1. The code for moving the Tello has been provided, however you are free to edit it.
You should complement the code with any packages you require, as well as updated API if any modifications were made.
'''

from Tello_api import Tello
from EP_api import Robot, findrobotIP
import cv2
import time


IMG_PATH = "/data/maze.jpg" # name of image captured by tello
NEW_IMG_PATH = "/data/maze_processed.jpg" # for scoring

# 1: Tello move and capture image. Manually adjust Tello with keyboard. Press spacebar to capture and save image, press enter to retrieve Tello
tello = Tello()

tello.startvideo() 
tello.startstates()

while tello.frame is None:
	pass

tello._sendcommand('takeoff')
tello.start_pad_det()
padreply = tello._sendcommand('jump 100 0 120 60 0 m1 m2') # x y z speed yaw pad_ids
if padreply == "ok":
		print("Reached m2")

while True:
	cv2.namedWindow('Tello video', cv2.WINDOW_NORMAL)
	cv2.imshow('Tello video', cv2.flip(tello.frame,0))

	k = cv2.waitKey(16) & 0xFF
	if k == 32: # spacebar to capture image 
		cv2.imwrite(IMG_PATH, cv2.flip(tello.frame,0))
		print(f'Saved as {IMG_PATH}!')
		cv2.imshow('Saved Image', cv2.flip(tello.frame,0)) 

	elif k == 13: # enter to retrieve drone, land and continue
		padreply = tello._sendcommand('jump -100 0 100 60 0 m2 m1') # x y z speed yaw pad_ids
		if padreply == "ok":
				print("Reached m1")
		print('Landing...')
		tello.exit()
		break

	elif k != -1:  # press wasdqe to adjust position of drone, uj to adjust height
		tello.act(k) 
cv2.destroyAllWindows()



# 2: Determine positions of start/end/obstacles (skip this step if not required in your solution)

# Apply your AI model here. Save your output file (for example, bounding boxes) to NEW_IMG_PATH, if any. Note that you either have to show your AI output during execution or as a saved image after the task. Refer to the Game Rules for more details.



# 3: Move Robot from Start to end
robot = Robot(findrobotIP())

# Replace this with your robot movement logic
'''
EXAMPLE: output an actionlist from step(2). 
for direction, magnitude in actionlist:
	if direction == 'left': 
		robot.rotate('-90')
	elif direction == 'right':
		robot.rotate('90')
	else: 
		robot.move(f'x {magnitude}')
'''

robot.exit()
