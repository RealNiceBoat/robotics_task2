import cv2
from models import get_human_model, get_clothes_model, get_most_confident, visualize, crop_bbox, id_to_label, metadata
from robot import Robot
import time

#nms is threshold for IoU, score is threshold for confidence
human_model = get_human_model(nms_thres=0.0,score_thres=0.95)
clothes_model = get_clothes_model(nms_thres=0.3,score_thres=0.75)
wanted_clothing = ['tops']

def find_doll(im):
    human_boxes = human_model(im)
    best_box = get_most_confident(human_boxes) #returns only 1 box in Boxes
    if len(best_box) == 0: return None,None,None
    box_area = best_box.area().tolist()[0]
    box_centre = best_box.get_centers().tolist()[0]
    cv2.imshow('Humanfeed',visualize(im,human_boxes))
    print(f'box area: {box_area}, box centre: {box_centre}')
    return best_box.tensor.tolist()[0],box_area,box_centre

with Robot('192.168.2.1') as robot:
    robot.reset_origin()
    robot.cam_doll()

    def check_doll():
        confirming_snaps = 5 #number of confirming pictures to take (the more the better)

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

            new_im,_ = crop_bbox(cur_im,best_box,b=0.1) #b is the extra margin
            outputs = clothes_model(new_im)['instances'].to('cpu')
            cv2.imshow('Clothesfeed',visualize(new_im,{'instances':outputs}))
            if len(outputs) == 0: continue

            classes = id_to_label(outputs.pred_classes.tolist())
            scores = outputs.scores.tolist()
            bboxes = outputs.pred_boxes.tensor.tolist()
            for cat,score,bbox in zip(classes,scores,bboxes):
                cat_scores[cat] += score
            snaps += 1

        print(cat_scores)
        for cat,score in cat_scores.items():
            if cat in wanted_clothing: doll_score += score
            else: doll_score -= 0.3*score #is arbitrary coefficient

        print(f'score: {doll_score}, threshold: {confirming_snaps*len(wanted_clothing)*0.5}')

    cv2.namedWindow('Livefeed', cv2.WINDOW_AUTOSIZE)
    while True:
        cv2.namedWindow('Humanfeed', cv2.WINDOW_AUTOSIZE)
        cv2.namedWindow('Clothesfeed', cv2.WINDOW_AUTOSIZE)
        check_doll()
        if cv2.getWindowProperty('Livefeed',cv2.WND_PROP_VISIBLE) < 1: break

    cv2.destroyAllWindows()