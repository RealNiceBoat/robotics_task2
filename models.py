import numpy as np
import cv2
from pathlib import Path

from detectron2 import model_zoo
from detectron2.engine.defaults import DefaultPredictor
from detectron2.config import get_cfg
from detectron2.utils.visualizer import Visualizer
from detectron2.data import MetadataCatalog,DatasetCatalog,build_detection_train_loader
from detectron2.data.datasets import register_coco_instances
from detectron2.structures import Boxes, Instances, BoxMode

#Paths
base_dir = Path('.')
clothes_model_path = base_dir/"ft-til_resnet101_rcnn_moda_aug-147999-best_val.pth"
categories_json = base_dir/"categories.json"
DatasetCatalog.clear()
register_coco_instances("categories", {}, categories_json, base_dir)


cfg_human = get_cfg()
cfg_human.merge_from_file(model_zoo.get_config_file("COCO-Keypoints/keypoint_rcnn_R_101_FPN_3x.yaml"))
cfg_human.MODEL.WEIGHTS = model_zoo.get_checkpoint_url("COCO-Keypoints/keypoint_rcnn_R_101_FPN_3x.yaml")

def get_human_model(nms_thres=0.0,score_thres=0.995):
    cfg_human.MODEL.ROI_HEADS.NMS_THRESH_TEST = nms_thres #IoU aka overlap suppression (suppress if overlap > threshold)
    cfg_human.MODEL.ROI_HEADS.SCORE_THRESH_TEST = score_thres #this isnt a confidence score filter... but seems to correlate well anyways
    human_model = DefaultPredictor(cfg_human)
    return human_model


cfg_clothes = get_cfg()
cfg_clothes.merge_from_file(model_zoo.get_config_file("COCO-Detection/faster_rcnn_R_101_FPN_3x.yaml"))
cfg_clothes.MODEL.WEIGHTS = str(clothes_model_path)
cfg_clothes.MODEL.ROI_HEADS.NUM_CLASSES = 5

cfg_clothes.DATASETS.TRAIN = ("categories",)
build_detection_train_loader(cfg_clothes) #force meta to load
metadata = MetadataCatalog.get("categories")
def id_to_label(ids): return [metadata.thing_classes[metadata.thing_dataset_id_to_contiguous_id[id]] for id in ids]

def get_clothes_model(nms_thres=0.2,score_thres=0.6):
    cfg_clothes.MODEL.ROI_HEADS.NMS_THRESH_TEST = nms_thres
    cfg_clothes.MODEL.ROI_HEADS.SCORE_THRESH_TEST = score_thres
    clothes_model = DefaultPredictor(cfg_clothes)
    return clothes_model

def display(im):
    cv2.namedWindow('Model Prediction', cv2.WINDOW_NORMAL)
    cv2.imshow('Model Prediction', im)
    while True:
        cv2.waitKey(100)
        if cv2.getWindowProperty('Model Prediction',cv2.WND_PROP_VISIBLE) < 1: break        
    cv2.destroyAllWindows()

def visualize(im,outputs):
    v = Visualizer(im, metadata, scale=1)
    v = v.draw_instance_predictions(outputs["instances"].to("cpu"))
    im_out = v.get_image()
    return im_out

def get_most_confident(outputs):
    outputs = outputs["instances"].to("cpu")
    bybest = sorted([(i,s) for i,s in enumerate(outputs.scores.tolist())],key=lambda x:x[1],reverse=True)
    return outputs[bybest[0][0]].pred_boxes

def crop_bbox(im,bbox,b=0.1):
    x1,y1,x2,y2 = bbox
    h,w = im.shape[:2]
    xf,yf = b*w,b*h
    x1,y1,x2,y2 = round(max(0,x1-xf)),round(max(0,y1-yf)),round(min(w,x2+xf)),round(min(h,y2+yf))
    return im[y1:y2,x1:x2],(x1,y1)

if __name__ == "__main__":
    im = cv2.imread("./unnamed.png")
    human_model = get_human_model()
    human_boxes = human_model(im)
    best_box = list(get_most_confident(human_boxes).tensor.tolist()[0])
    new_im,offset = crop_bbox(im,best_box,b=0.1) #b is the extra margin
    clothes = get_clothes_model(nms_thres=0.2,score_thres=0.6) #nms is threshold for IoU, score is threshold for confidence
    outputs = clothes(new_im)
    display(visualize(new_im,outputs))