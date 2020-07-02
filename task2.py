from time import sleep
import cv2
from models import get_human_model, get_clothes_model, get_most_confident, visualize, crop_bbox, id_to_label
from robot import Robot

def find_doll(im,model):
    '''TODO: should be run in separate thread? non-blocking callback based?'''
    human_boxes = model(im)
    best_box = get_most_confident(human_boxes) #returns only 1 box in Boxes
    box_area = best_box.area().tolist()[0]
    box_centre = best_box.get_centers().tolist()[0]
    cv2.imshow('Humanfeed',visualize(cur_im,human_boxes))
    print(f'box area: {box_area}, box centre: {box_centre}')
    return best_box.tensor.tolist()[0],box_area,box_centre

def check_box_is_doll(box_area):
    '''TODO: better checking, add more params as needed'''
    #TODO: some threshold size? besides box size and confidence thresholding, how to detect dolls accurately? or hardcode motion?
    return abs(box_area-66666) < 300

def grip_doll(robot):
    '''TODO: movement routine to grab doll'''
    #TODO: might need to move forward till bbox is certain size?
    raise NotImplementedError

#nms is threshold for IoU, score is threshold for confidence
human_model = get_human_model(nms_thres=0.2,score_thres=0.6)
clothes_model = get_clothes_model(nms_thres=0.2,score_thres=0.6)

wanted_clothing = set((lambda x: [x])(1)) #(expecting a list from imported function @haohui)
dolls_found = 0

isTuning = False

if not isTuning: input('Enter anything to begin.')

#TODO: pLeasE PlacE the bOT 30cm fRom dOLL, how to keep distance from dolls constant? what if dolls arent in straight line?
with Robot('192.168.1.2') as robot:
    robot.reset_origin()
    robot.cam_doll()
    #ini_orientation = robot.pos[2]

    cv2.namedWindow('Livefeed',cv2.WINDOW_NORMAL)
    while dolls_found < 3 or isTuning: 
        cv2.namedWindow('Humanfeed',cv2.WINDOW_NORMAL)
        cv2.namedWindow('Clothesfeed',cv2.WINDOW_NORMAL)

        cv2.waitKey(10)
        #Close livefeed window to force stop
        if cv2.getWindowProperty('Livefeed',cv2.WND_PROP_VISIBLE) < 1: 
            print("Stopping!")
            break

        if not robot.hasNewFrame: continue
        robot.hasNewFrame = False

        cur_im = robot.frame.copy()
        cv2.imshow('Livefeed',cur_im)

        '''Step 1: find doll box'''
        best_box,box_area,box_centre = find_doll(cur_im,human_model)
        if not check_box_is_doll(box_area): continue

        '''Step 2: centre on doll box'''
        e = box_centre[0] - 1920/2 #1080p resolution, error is in pixels
        #TODO: PID??? below centralizes bot to doll
        #TODO: correction to ensure robot remains oriented to ini_orientation?
        if e > 5: robot.speed(x=50)
        elif e < -5: robot.speed(x=-50)
        if e >= 5: continue

        '''Step 3: identify doll'''
        robot.brake()
        #TODO: move towards doll?
        new_im,offset = crop_bbox(cur_im,best_box,b=0.1) #b is the extra margin
        outputs = clothes_model(new_im)
        cv2.imshow('Clothesfeed',visualize(new_im,outputs))

        present_classes = id_to_label(outputs['instances'].pred_classes.tolist())

        #TODO: Better way to evaluate for match (current is: confidence filter, then subset check)
        if wanted_clothing.issubset(present_classes):
            robot.light_green()
            grip_doll(robot)
        else:
            robot.light_red()
        
        dolls_found += 1

    print("Completed!")            
    cv2.destroyAllWindows()

'''
https://robomaster-dev.readthedocs.io/en/latest/sdk/api.html
'''

'''
my current plan:
0. Function that resets arm abs position for camera to be ideally positioned
1. move robot left/right till only 1 large & high confidence bounding box
2. Centralize bounding box, move inwards till certain area, take image, crop around the box, do identification
3. No need exact match! The clothes requested should just be within the bounding box list (cut out low confidence predictions without increasing NMS threshold)
4. if match, move inwards while keeping bounding box centralized till certain size, then execute hardcoded wiggle and pick routine

^ALWAYS KEEP THE ROTATION OF BOT FORWARDS, SO MOVE LEFT RIGHT TO ADJUST NOT ROTATE
^maybe dont move inwards for 2, else have to move outwards again lest we hit down a doll, after 1080p is enough to crop since our model was trained on 400x600
^sanity check: Skirt is large area, top is top, trousers is bottom, etc, if its weird -0.5 from cofidence or smth
'''