
from EP_api import findrobotIP, Robot
import cv2
import time
import threading
import argparse

import colorsys
import numpy as np
from timeit import default_timer as timer
from PIL import Image, ImageFont, ImageDraw
from extract_clothes import get_clothes_class


'''
A simple matching algorithm
'''
def filter_detections(target_clothing, results):
    boxes, scores, classes = results

    filtered_boxes, filtered_scores, filtered_classes_str =  [], [], []

    for i in range(len(classes)):
      if classes[i] in target_clothing: # or classes[i] in target_bottom:
          filtered_boxes.append(boxes[i])
          filtered_scores.append(scores[i])
          filtered_classes_str.append(classes[i])

    return [filtered_boxes, filtered_scores, filtered_classes_str]

'''
A simple visualisation function for results
'''
def visualize(image, outputs):
    out_boxes, out_scores, out_classes_str = outputs

    font = ImageFont.truetype(font='font/FiraMono-Medium.otf', size=np.floor(3e-2 * image.size[1] + 0.5).astype('int32'))
    thickness = (image.size[0] + image.size[1]) // 300

    # Generate colors for drawing bounding boxes.
    num_unique_labels = 2 
    hsv_tuples = [(x / num_unique_labels, 1., 1.) for x in range(num_unique_labels)]
    colors = list(map(lambda x: colorsys.hsv_to_rgb(*x), hsv_tuples))
    colors = list(map(lambda x: (int(x[0] * 255), int(x[1] * 255), int(x[2] * 255)), colors))
    np.random.seed(10101)  # Fixed seed for consistent colors across runs.
    np.random.shuffle(colors)  # Shuffle colors to decorrelate adjacent classes.
    np.random.seed(None)  # Reset seed to default.

    for i, c in list(enumerate(out_classes_str)):
        predicted_class = out_classes_str[i]
        box = out_boxes[i]
        score = out_scores[i]
        
        label = '{} {:.2f}'.format(predicted_class, score)
        draw = ImageDraw.Draw(image)
        label_size = draw.textsize(label, font)

        top, left, bottom, right = box
        top = max(0, np.floor(top + 0.5).astype('int32'))
        left = max(0, np.floor(left + 0.5).astype('int32'))
        bottom = min(image.size[1], np.floor(bottom + 0.5).astype('int32'))
        right = min(image.size[0], np.floor(right + 0.5).astype('int32'))
        # print(label, (left, top), (right, bottom))

        if top - label_size[1] >= 0:
            text_origin = np.array([left, top - label_size[1]])
        else:
            text_origin = np.array([left, top + 1])

        for i in range(thickness):
            draw.rectangle([left + i, top + i, right - i, bottom - i], outline='green')
      
        draw.rectangle(
            [tuple(text_origin), tuple(text_origin + label_size)],
            fill='green')
      
        draw.text(text_origin, label, fill=(0, 0, 0), font=font)
      
        del draw

    return image

''' Fill in your robotic response here '''
def move_robot():
	return None


def close_stream(robot):
    print("Quitting...")
    robot.exit()


def main():
    robot_ip = findrobotIP()
    robot = Robot(robot_ip)
    robot.startvideo()
    while robot.frame is None:
        pass
    robot._sendcommand('camera exposure high')

    # Init Variables
    img_counter = 0
    accum_time = 0
    curr_fps = 0
    fps = "FPS: ??"
    prev_time = timer()
    count = 0

    ########## Use this to prompt for an input mission ########## 
    txt = input("input mission statement: ")
    print('Mission statement', txt)

    '''
    Insert your clothing article extractor here, we provided a simple library to convert your plain text into the encoded format if you would like to use your previous models. 
    We provided an example of how you can use the provided extract_clothes class here
  	
  	e.g. desired_clothing = ['women dresses'] 
    '''
    #extractor = get_clothes_class(model_path, tokenizer_path, encoded_words_dict_path)
    #desired_clothing = extractor.process_input(txt)    
    
    print ('Extracted target clothing article: ',desired_clothing)

    ### Initialise the robot to run on autonomous mode
    mode = 'auto'
    # Lift arm up to elevate the camera angle
    robot._sendcommand('robotic_arm moveto x 210 y 64')
    time.sleep(1)

    while True:

        cv2.namedWindow('Live video', cv2.WINDOW_NORMAL)
        cv2.imshow('Live video', robot.frame)

        # Key listener
        k = cv2.waitKey(16) & 0xFF


        ''' To provide toggle on keyboard between manual driving and autonomous driving '''
        if k == ord('m'):
            print('manual mode activated')
            mode = 'manual'

        if k == ord('n'):
            print('autonomous mode activated')
            mode = 'auto'

        if k == 27: # press esc to stop
            close_stream(robot)
            cv2.destroyWindow("result")
            cv2.destroyWindow("Live video")
            break

        frame = robot.frame
        frame_h, frame_w, frame_channels = frame.shape

        '''
        This set of codes is used for manual control of robot
        '''
        if mode == 'manual':            
            if k == ord('p'):
              robot.scan()
            
            if k == ord('w'):
              robot._sendcommand('chassis move x 0.2')

            elif k == ord('a'):
              robot._sendcommand('chassis move y -0.2')

            elif k == ord('s'):
              robot._sendcommand('chassis move x -0.2')

            elif k == ord('d'):
              robot._sendcommand('chassis move y 0.2')
            elif k == ord('q'):
              robot._sendcommand('chassis move z -5')
            elif k == ord('e'):
              robot._sendcommand('chassis move z 5')

            # elif k == ord('i'): # up and down arrow sometimes dont work
            #   robot._sendcommand('gimbal move p 1')
            # elif k == ord('k'): 
            #   robot._sendcommand('gimbal move p -1')
            # elif k == ord('j'): # up and down arrow sometimes dont work
            #   robot._sendcommand('gimbal move y -1')
            # elif k == ord('l'): 
            #   robot._sendcommand('gimbal move y 1')

            elif k == ord('r'): 
              robot._sendcommand('robotic_arm recenter')
            elif k == ord('x'): 
              robot._sendcommand('robotic_arm stop')
            elif k == ord('c'): 
              robot._sendcommand('robotic_arm moveto x 210 y 44')
            elif k == ord('z'): 
              robot._sendcommand('robotic_arm moveto x 92 y 90')
            elif k == ord('f'):     
              robot._sendcommand('robotic_gripper open 1')
            elif k == ord('g'): 
              robot._sendcommand('robotic_gripper close 1')

        elif mode=='auto':

        	print('Switched to autonomous control')

            #image = Image.fromarray(frame.copy())
            
            '''
            Insert your model here 
            '''
            #raw_image, outputs = model.predict(frame.copy())
            
            '''
            INSERT YOUR ROBOT RESPONSE MOVEMENT HERE
            '''
            #if len(outputs) > 0:
                # cmd_str = move_robot(outputs)

            '''
            The following code is used to draw the resulting image 
            '''  
            # image_filtered = visualize(image.copy(), outputs)
            # image_final = np.array(image_filtered)

            # curr_time = timer()            
            # exec_time = curr_time - prev_time
            # prev_time = curr_time
            # accum_time = accum_time + exec_time
            # curr_fps = curr_fps + 1
            
            # if accum_time > 1:
            #     accum_time = accum_time - 1
            #     fps = "FPS: " + str(curr_fps)
            #     curr_fps = 0
            
            # cv2.putText(image_final, text=fps, org=(3, 35), fontFace=cv2.FONT_HERSHEY_SIMPLEX,
            #             fontScale=1.2, color=(0, 255, 0), thickness=2)
        
            # cv2.namedWindow("result", cv2.WINDOW_NORMAL)
            # cv2.imshow("result", image_final)



if __name__ == '__main__':
    main()


