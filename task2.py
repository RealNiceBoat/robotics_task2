import cv2
from models import get_human_model, get_clothes_model, get_most_confident, visualize, crop_bbox, id_to_label, metadata
from robot import Robot,PID
from extract_clothes import get_clothes_class
import time

#nms is threshold for IoU, score is threshold for confidence
human_model = get_human_model(nms_thres=0.01,score_thres=0.9)
clothes_model = get_clothes_model(nms_thres=0.3,score_thres=0.7)
clothes_text = get_clothes_class(".","./encoded_words.pkl")

def find_doll(im,min_area=0,max_area=100000):
    human_boxes = human_model(im)
    best_box = get_most_confident(human_boxes,min_area,max_area) #returns only 1 box in Boxes
    if len(best_box) == 0: return None,None,None
    box_area = best_box.area().tolist()[0]
    box_centre = best_box.get_centers().tolist()[0]
    cv2.imshow('Humanfeed',visualize(im,human_boxes))
    print(f'box area: {box_area}, box centre: {box_centre}')
    return best_box.tensor.tolist()[0],box_area,box_centre

cv2.namedWindow('Livefeed', cv2.WINDOW_AUTOSIZE)
cv2.namedWindow('Humanfeed', cv2.WINDOW_AUTOSIZE)
cv2.namedWindow('Clothesfeed', cv2.WINDOW_AUTOSIZE)

doll_pos = -1
with Robot() as robot:
    robot.reset_origin()
    robot.cam_doll()

    wanted_clothing = clothes_text.process_input(input("Enter description: "))
    print(wanted_clothing)

    '''Get to the centre of task 2 zone
    
    if plan==1: robot.move(x=0.6,y=0.8)
    elif plan==2: robot.move(x=0.6,y=0.0)
    elif plan==3: robot.move(x=0.6,y=-0.8)
    #if diagonals fail/cause rotation, decompose this motion
    '''
    robot.move(x=0.8) #get off exit completely
    
    def check_doll():
        move_zoom = 0.5#0.3 #move forward to get clearer view (can try setting to 0)
        confirming_snaps = 10 #number of confirming pictures to take (the more the better)
        robot.move(x=move_zoom)

        cat_scores = {k:0.0 for k in metadata.thing_classes}
        doll_score = 0.0
        snaps = 0 #number of pictures taken
        while snaps < confirming_snaps:
            if not robot.hasNewFrame: continue
            robot.hasNewFrame = False
            cur_im = robot.frame.copy()
            cv2.imshow('Livefeed',cur_im)

            cv2.waitKey(1)
            if cv2.getWindowProperty('Livefeed',cv2.WND_PROP_VISIBLE) < 1: break

            best_box,_,_ = find_doll(cur_im)
            if best_box is None:
                cv2.imshow('Humanfeed',cur_im)
                continue

            new_im,_ = crop_bbox(cur_im,best_box,b=0.05) #b is the extra margin
            outputs = clothes_model(new_im)['instances'].to('cpu')
            cv2.imshow('Clothesfeed',visualize(new_im,{'instances':outputs}))
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
        isCorrect = doll_score > confirming_snaps*len(wanted_clothing)*0.4 #last one is sureness
        if isCorrect: robot.light_green()
        else: robot.light_red()

        robot.move(x=-move_zoom)
        return isCorrect

    box_pid = PID(1280.0/2,0.2500,0.0,0.0)
    def grab_doll():
        robot.open_claw()
        prev_time = time.time()
        while True:
            if not robot.hasNewFrame: continue
            robot.hasNewFrame = False
            cur_im = robot.frame.copy()
            cv2.imshow('Livefeed',cur_im)

            cv2.waitKey(1)
            if cv2.getWindowProperty('Livefeed',cv2.WND_PROP_VISIBLE) < 1: break
            
            best_box,box_area,box_centre = find_doll(cur_im)
            if best_box is None:
                cv2.imshow('Humanfeed',cur_im)
                robot.brake()
                continue

            cur_time = time.time()
            val = box_pid.update(box_centre[0],cur_time-prev_time)
            prev_time = cur_time

            robot.speed(x=35,z=-val)
            print(f'Bottom Edge: {best_box[3]}, PID Turn %{-val}')

            if (box_area > 54000 and best_box[3] > 690): #for 720p #box_area > 64000 #abs(val) < 15 and #TODO: TUNE THIS
                if -val > 5: robot.turn(8)
                elif -val < -5: robot.turn(-8)
                robot.move(x=0.3,speed=0.1)
                break
        #TODO: find better way than this
        #robot.move(x=0.2,speed=0.1)
        robot.close_claw()
        time.sleep(1)

    
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