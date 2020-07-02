import cv2
from models import get_human_model, get_clothes_model, get_most_confident, visualize, crop_bbox, id_to_label
from robot import Robot,PID
from extract_clothes import get_clothes_class
import time

#nms is threshold for IoU, score is threshold for confidence
human_model = get_human_model(nms_thres=0.001,score_thres=0.95)
clothes_model = get_clothes_model(nms_thres=0.3,score_thres=0.75)
box_pid = PID(1920/2,1.0,0,0.0) #1080p
clothes_text = get_clothes_class(".","./encoded_words.pkl")

def find_doll(im):
    human_boxes = human_model(im)
    best_box = get_most_confident(human_boxes) #returns only 1 box in Boxes
    if len(best_box) == 0: return None,None,None
    box_area = best_box.area().tolist()[0]
    box_centre = best_box.get_centers().tolist()[0]
    #cv2.imshow('Humanfeed',visualize(cur_im,human_boxes))
    print(f'box area: {box_area}, box centre: {box_centre}')
    return best_box.tensor.tolist()[0],box_area,box_centre

wanted_clothing = clothes_text.process_input(input("Enter description: "))
print(wanted_clothing)

doll_pos = -1
with Robot() as robot:
    robot.reset_origin()
    robot.cam_doll()

    '''Get to the centre of task 2 zone
    robot.move(x=0.4) #get off exit completely
    if plan==1: robot.move(x=0.6,y=0.8)
    elif plan==2: robot.move(x=0.6,y=0.0)
    elif plan==3: robot.move(x=0.6,y=-0.8)
    #if diagonals fail/cause rotation, decompose this motion
    '''
    
    def check_doll():
        move_zoom = 0.3 #move forward to get clearer view (can try setting to 0)
        confirming_snaps = 5 #number of confirming pictures to take (the more the better)
        robot.move(x=move_zoom)

        cat_scores = {
            "tops":0.0,
            "trousers":0.0,
            "outerwear":0.0,
            "dresses":0.0,
            "skirts":0.0
        }
        doll_score = 0.0
        snaps = 0 #number of pictures taken
        while snaps < confirming_snaps:
            if not robot.hasNewFrame: continue
            robot.hasNewFrame = False
            cur_im = robot.frame.copy()

            best_box,_,_ = find_doll(cur_im)
            if best_box is None: continue

            new_im,_ = crop_bbox(cur_im,best_box,b=0.1) #b is the extra margin
            outputs = clothes_model(new_im)['instances'].to('cpu')
            if len(outputs) == 0: continue

            classes = id_to_label(outputs.pred_classes.tolist())
            scores = outputs.scores.tolist()
            bboxes = outputs.pred_boxes.tensor.tolist()
            for cat,score,bbox in zip(classes,scores,bboxes):
                #TODO: use bbox to check if valid. aka everything about dresses is less than 0.8*area, tops are on top, skirts are below...
                cat_scores[cat] += score
            snaps += 1

        print(cat_scores)
        for cat,score in cat_scores.items():
            #TODO: subtract only for clearly contradictory clothes item, in case request only trousers but the doll wears trousers + top?
            if cat in wanted_clothing: doll_score += score
            else: doll_score -= 0.3*score #is arbitrary coefficient

        print(doll_score) #tbh should be returning this to rank... but if that was necessary, LED misdetect already happened.
        if doll_score > confirming_snaps*len(wanted_clothing)*0.5: #last one is sureness
            robot.light_green()
            robot.move(x=-move_zoom)
            return True
        else:
            robot.light_red()
            robot.move(x=-move_zoom)
            return False

    def grab_doll():
        robot.open_claw()
        prev_time = time.time()
        while True:
            if not robot.hasNewFrame: continue
            robot.hasNewFrame = False
            cur_im = robot.frame.copy()
            
            best_box,box_area,box_centre = find_doll(cur_im)
            if best_box is None: continue

            cur_time = time.time()
            val = box_pid.update(box_centre[0],cur_time-prev_time)
            prev_time = cur_time

            robot.move(x=0.1,y=val,buffer=0.0) #pid corrected box alignment lol
            
            if box_area > 750*350: break #TODO: Tune this area
        
        robot.speed(x=10) #MOVE VERY SLOWLY so as to not push doll over?
        time.sleep(10) #as long as we need to be sure it is in the claw
        #TODO: find better way than this
        robot.close_claw()
        robot.brake()

    
    #facing forwards
    if check_doll(): doll_pos = 2
    robot.turn(-90)
    #facing left
    if check_doll(): doll_pos = 1
    robot.turn(180)
    #facing right
    if check_doll(): doll_pos = 3

    #from facing right...
    if doll_pos==1: robot.turn(-180)
    elif doll_pos==2: robot.turn(-90)
    elif doll_pos==3: pass
    grab_doll()

    print("Completed!")

'''
https://robomaster-dev.readthedocs.io/en/latest/sdk/api.html
'''