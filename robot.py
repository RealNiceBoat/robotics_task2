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
        self.hasNewFrame = False
        self.stream = None
        self.pos = [0,0,0]

    def open(self):
        self.cmd_feedback_thread = Thread(target=self.__recvmsg)
        self.vid_receive_thread = Thread(target=self.__recvvideo,daemon=True)
        self.push_thread = Thread(target=self.__recvpush)
        
        try:
            self.ctrl_sock.connect((self.ip,CTRL_PORT))
            self.isOpen = True
            self.send('command')
            self.push_sock.connect((self.ip,PUSH_PORT))
        except Exception as e:
            self.close()
            raise(e)

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
        #self.cmd_feedback_thread.join()
        #self.vid_receive_thread.join()
        #self.push_thread.join()
        print(f"Disconnected from {self.ip}")
    
    def send(self,*args):
        '''Send commands directly! If there is multiple args it will join them with spaces.'''
        assert(self.isOpen)
        cmdstring = ' '.join([str(a) for a in args])+';'
        self.ctrl_sock.sendall(cmdstring.encode('utf8'))
        print(f'Sent: {cmdstring}')

    def __recvvideo(self):
        self.send('stream on')
        sleep(0.5)
        #self.send('camera exposure high') #i saw this in their example code
        self.stream = cv2.VideoCapture(f'tcp://@{self.ip}:{VIDEO_PORT}')
        while self.stream.isOpened() and self.isOpen: 
            _, self.frame = self.stream.read()
            self.hasNewFrame = True

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
        Move robot in metres relative to current position (will move diagonally). Speed limit of 0.3m/s.
        - x (number, default: 0.0): distance in x axis to move in metres
        - y (number, default: 0.0): distance in y axis to move in metres
        - wait (bool, default: True): whether to wait for action to complete
        '''
        self.send('chassis','move','x',y,'y',x,'vxy',SPD_LIMIT)
        if wait: sleep(calculate_move_time(x,y)+BUFFER_TIME)

    def speed(self,x=.0,y=.0):
        '''
        Move robot at speed (% of 0.3m/s) (will move diagonally). Speed limit of 0.3m/s.
        - x (number, default: 0.0): between -100 to 100
        - y (number, default: 0.0): between -100 to 100
        '''
        self.send('chassis','speed','x',y/100.0*SPD_LIMIT,'y',x/100.0*SPD_LIMIT) #doesnt account for diagonals properly
    def brake(self): self.speed()

    def turn(self,ang,wait=True):
        '''
        Rotate robot in degrees relative to current rotation. Speed limit of 10deg/s.
        - ang (number): angle to turn in degrees
        - wait (bool, default: True): whether to wait for action to complete
        '''
        self.send('chassis','move','z',ang,'vz',TURN_LIMIT)
        if wait: sleep(calculate_turn_time(ang)+BUFFER_TIME) #TODO: doesnt work for the 0-> 359 issue

    def reset_origin(self):
        self.send('robotic_arm','move','x',-500,'y',-500)
        sleep(1)
        #TODO: transformation layer over chassis position and robot arm position
        #transformation layer not necessary if arm motion is relative to this lowest position!

    def cam_doll(self):
        '''TODO: Move arm to position where camera is facing forwards'''
        self.send('robotic_arm','move','x',10,'y',20) #in cm
        sleep(1)
        #raise NotImplementedError

    def cam_ground(self):
        '''TODO: Move arm to position where camera is facing ground'''
        self.send('robotic_arm','move','x',210,'y',64) #in cm
        sleep(1)
        #raise NotImplementedError

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
    #python -i robot.py
    robot = Robot().open()
    robot.reset_origin()
    robot.cam_doll()