#Adapted from https://github.com/dji-sdk/RoboMaster-SDK/tree/master/sample_code/RoboMasterEP
import socket
import cv2
from threading import Thread
from time import sleep

VIDEO_PORT = 40921
AUDIO_PORT = 40922
CTRL_PORT = 40923
PUSH_PORT = 40924
EVENT_PORT = 40925
IP_PORT = 40926

SPD_LIMIT = 0.3
TURN_LIMIT = 10
BUFFER_TIME = 0.5 #in seconds

def calculate_move_time(x,y): return (x**2+y**2)**0.5/float(SPD_LIMIT)
def calculate_turn_time(ang): return abs(float(ang)/TURN_LIMIT)

def find_robot_ip(timeout=None):
    '''Finds the IP address broadcasted by the robot'''
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
        s.settimeout(timeout)
        s.bind(('',IP_PORT))
        data,addr = s.recvfrom(1024)
        print(f'UDP Broadcast from {addr}: {data}')
        return addr[0]

class Robot:
    '''Class to wrap around robot's text based SDK'''
    def __enter__(self): return self.open()
    def __exit__(self,exc_type,exc_val,exc_tb): self.close()
    
    def __init__(self,robot_ip=None):
        '''
        Connects to the robot & initializes services.
        - robot_ip (string, default: None): IP to connect to, if None will look for robot's broadcast.
        '''
        self.ip = find_robot_ip() if robot_ip is None else robot_ip

        #self.audio_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ctrl_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.push_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #self.event_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.isOpen = False
        self.frame = None
        self.stream = None
        self.pos = [0,0,0]

    def open(self):
        self.cmd_feedback_thread = Thread(target=self.__recvmsg)
        self.vid_receive_thread = Thread(target=self.__recvvideo)
        self.push_thread = Thread(target=self.__recvpush)
        
        try:
            self.ctrl_sock.connect((self.ip,CTRL_PORT))
            self.send('command')
            self.push_sock.connect((self.ip,PUSH_PORT))
        except Exception as e:
            self.close()
            raise(e)

        self.isOpen = True
        self.cmd_feedback_thread.start()
        self.push_thread.start()
        self.vid_receive_thread.start()
        print(f"Connected to {self.ip}")
        return self
    
    def close(self):
        try:
            self.send('stream off')
            self.send('quit')
        except:
            pass
        self.isOpen = False
        self.ctrl_sock.close()
        self.stream.release()
        self.cmd_feedback_thread.join()
        self.vid_receive_thread.join()
        self.push_thread.join()
        print(f"Disconnected from {self.ip}")
    
    def send(self,*args):
        '''Send commands directly! If there is multiple args it will join them with spaces.'''
        assert(self.isOpen)
        cmdstring = ' '.join(args)+';'
        self.ctrl_sock.sendall(cmdstring.encode('utf8'))
        print(f'Sent: {cmdstring}')

    def __recvvideo(self):
        self.send('stream on')
        self.send('camera exposure high') #i saw this in their example code
        self.stream = cv2.VideoCapture(f'tcp://@{self.ip}:{VIDEO_PORT}')
        while self.stream.isOpened() and self.isOpen: 
            _, self.frame = self.stream.read()

    def __recvmsg(self):
        while self.isOpen:
            raw = self.ctrl_sock.recv(1024)
            print(f'Received: {raw.decode("utf-8")}')

    def __recvpush(self):
        self.send('chassis push position on pfreq 20 attitude on afreq 20') #receive data 20Hz
        while self.isOpen:
            raw = self.ctrl_sock.recv(1024)
            #TODO: does it contain a ; on the end?
            data = raw.decode('utf-8').split(' ')
            if data[:3] == ['chassis','push','position']:
                self.pos[0],self.pos[1] = data[3],data[4]
            elif data[:3] == ['chassis','push','attitude']:
                self.pos[2] = data[5]


    ##################
    # ROBOT COMMANDS #
    ##################

    def move(self,x=.0,y=.0,wait=True):
        '''
        Move robot in metres relative to absolute origin (will move diagonally). Speed limit of 0.3m/s.
        - x (number, default: 0.0): distance in x axis to move in metres
        - y (number, default: 0.0): distance in y axis to move in metres
        - wait (bool, default: True): whether to wait for action to complete
        '''
        self.send('chassis','move','x',x,'y',y,'vxy',SPD_LIMIT)
        if wait: sleep(calculate_move_time(x-self.pos[0],y-self.pos[1])+BUFFER_TIME)

    def speed(self,x=.0,y=.0):
        '''
        Move robot at speed (% of 0.3m/s) (will move diagonally). Speed limit of 0.3m/s.
        - x (number, default: 0.0): -100 <= x <= 100
        - y (number, default: 0.0): -100 <= y <= 100
        '''
        self.send('chassis','speed','x',x/100.0*SPD_LIMIT,'y',y/100.0*SPD_LIMIT) #doesnt account for diagonals properly
    def brake(self): self.speed()

    def turn(self,ang,wait=True):
        '''
        TODO: I dont know if positive is clockwise... relative to absolute origin. Speed limit of 10deg/s.
        - ang (number): angle to turn in degrees
        - wait (bool, default: True): whether to wait for action to complete
        '''
        self.send('chassis','move','z',ang,'vz',TURN_LIMIT)
        if wait: sleep(calculate_turn_time(ang-self.pos[2])+BUFFER_TIME) #TODO: doesnt work for the 0-> 359 issue

    def reset_arm(self):
        '''TODO: So its calibrated to the robot arm's position at robot boot... Great... This will need constant retuning if we dont reset the arm at shutdown. Just move the arm as inwards and low as it can for reset?'''
        self.send('robotic_arm','moveto','x',50000,'y',50000) #in cm
        #reboots robot... guess not
        raise NotImplementedError

    def cam_doll(self):
        '''TODO: Move arm to position where camera is facing forwards'''
        self.send('robotic_arm','moveto','x',50,'y',50) #in cm
        sleep(1)
        raise NotImplementedError

    def cam_ground(self):
        '''TODO: Move arm to position where camera is facing ground'''
        self.send('robotic_arm','moveto','x',210,'y',64) #in cm
        sleep(1)
        raise NotImplementedError

    def grip_doll(self):
        '''TODO: movement routine to grab doll'''
        raise NotImplementedError

    def open_arm(self):
        self.send('robotic_gripper open 1')
        sleep(1)
    def close_arm(self):
        self.send('robotic_gripper close 1')
        sleep(1)

    def light_red(self): 
        self.send('led control comp bottom_all r 255 g 0 b 0 effect solid')
        sleep(1)
        self.send('led control comp bottom_all r 255 g 255 b 255 effect solid')

    def light_green(self):
        self.send('led control comp bottom_all r 0 g 255 b 0 effect solid')
        sleep(1)
        self.send('led control comp bottom_all r 255 g 255 b 255 effect solid')

if __name__ == "__main__":
    #this is task2. I hope task1 is as simple as executing a list of instructions
    from models import get_human_model, get_clothes_model, get_most_confident, visualize, crop_bbox, id_to_label

    human_model = get_human_model()
    clothes_model = get_clothes_model(nms_thres=0.2,score_thres=0.6) #nms is threshold for IoU, score is threshold for confidence

    wanted_clothing = set((lambda x: [x])(1)) #(expecting a list from imported function @haohui)

    dolls = 0

    #TODO: pLeasE PlacE the bOT 30cm fRom dOLL, how to keep distance from dolls constant? what if dolls arent in straight line?
    with Robot('192.168.1.2') as robot:
        robot.cam_doll()
        ini_orientation = robot.pos[2]

        cv2.namedWindow('Livefeed',cv2.WINDOW_NORMAL)
        while dolls < 3:
            #recreate windows in case you closed them idiot
            
            cv2.namedWindow('Humanfeed',cv2.WINDOW_NORMAL)
            cv2.namedWindow('Clothesfeed',cv2.WINDOW_NORMAL)

            cv2.waitKey(10)
            if cv2.getWindowProperty('Livefeed',cv2.WND_PROP_VISIBLE) < 1: #code can be forced stop by closing livefeed window
                print("Stopping!")
                break

            cur_im = robot.frame.copy()
            cv2.imshow('Livefeed',cur_im)

            #TODO: should be run in separate thread?
            human_boxes = human_model(cur_im)
            best_box = get_most_confident(human_boxes) #returns only 1 box in Boxes
            box_area = best_box.area().tolist()[0]
            box_centre = best_box.get_centers().tolist()[0]
            cv2.imshow('Humanfeed',visualize(cur_im,human_boxes))
            print(f'box area: {box_area}, box centre: {box_centre}')

            #TODO: some threshold size??? besides box size and confidence thresholding, can also use clothes detector... what if dont detect...
            #how to detect dolls accurately? or hardcode motion?
            if abs(box_area-9000) < 300:
                e = box_centre[0] - 1920/2 #1080p resolution, error is in pixels
                #TODO: PID??? below centralizes bot to doll
                #TODO: correction to ensure robot remains oriented to ini_orientation? robot.turn(0)
                if e > 5:
                    robot.speed(x=50)
                elif e < -5:
                    robot.speed(x=-50)
                else:
                    robot.brake()
                    #TODO: move towards doll?
                    new_im,offset = crop_bbox(cur_im,best_box.tensor.tolist()[0],b=0.1) #b is the extra margin
                    outputs = clothes_model(new_im)
                    cv2.imshow('Clothesfeed',visualize(new_im,outputs))

                    present_classes = id_to_label(outputs['instances'].pred_classes.tolist())
                    if len(present_classes) == 0: continue #further subroutine needed to ignore the fake box
                    #TODO: Better way to evaluate for match (current is: confidence filter, then subset check)
                    if wanted_clothing.issubset(present_classes):
                        robot.light_green()
                        robot.grip_doll() #TODO: might need to move forward till bbox is certain size?
                    else:
                        robot.light_red()
                    
                    dolls += 1

        print("Completed!")            
        cv2.destroyAllWindows()

'''
https://robomaster-dev.readthedocs.io/en/latest/sdk/api.html
'''

'''
Boxes.area() #tensor array of area of each box
Boxes.nonempty(pixel_threshold) #keep boxes whose width & height are greater than threshold
Boxes.get_centers() #tensor array of (x,y) of centre of boxes
Boxes.scale(x,y) #rescale boxes by factor x and y
BoxMode.convert(boxes,XYXY_ABS,XYWH_ABS) #convert boxes from mode to mode (please only do this at the end, the above functions only work correctly for XYXY)
'''

'''
my current plan:
0. Function that resets arm abs position for camera to be ideally positioned
1. human cropper running in fast mode (high thres NMS), move robot left/right till only 1 large & high confidence bounding box
2. Centralize bounding box, move inwards till certain area, take image, crop around the box, do identification
3. No need exact match! The clothes requested should just be within the bounding box list (cut out low confidence predictions without increasing NMS threshold)
4. if match, move inwards while keeping bounding box centralized till certain size, then execute hardcoded wiggle and pick routine

^ALWAYS KEEP THE ROTATION OF BOT FORWARDS, SO MOVE LEFT RIGHT TO ADJUST NOT ROTATE
^maybe dont move inwards for 2, else have to move outwards again lest we hit down a doll, after 1080p is enough to crop since our model was trained on 400x600
^sanity check: Skirt is large area, top is top, trousers is bottom, etc, if its weird -0.5 from cofidence or smth
'''
        




        