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

def calculate_move_time(x,y,spd): return (x**2+y**2)**0.5/float(spd)
def calculate_turn_time(ang,spd): return abs(float(ang)/spd)

def find_robot_ip(timeout=None):
    '''Finds the IP address broadcasted by the robot'''
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
        s.settimeout(timeout)
        s.bind(('',IP_PORT))
        data,addr = s.recvfrom(1024)
        print(f'UDP Broadcast from {addr}: {data}')
        return addr[0]

class Robot:
    '''Class to wrap around robot's text based SDK. +x is forwards, +y is right.'''
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
        self.isOpen = True

        try:
            self.ctrl_sock.connect((self.ip,CTRL_PORT))
            self.cmd_feedback_thread.start()
            self.send('command')
            self.push_sock.connect((self.ip,PUSH_PORT))
            #self.push_thread.start()
            self.vid_receive_thread.start()
        except Exception as e:
            self.close()
            raise(e)
        self.send('led control comp bottom_all r 255 g 255 b 255 effect solid')
        print(f"Connected to {self.ip}")
        return self
    
    def close(self):
        try:
            self.send('stream off')
            self.send('quit')
        except:
            pass
        self.isOpen = False
        try:
            self.ctrl_sock.close()
            self.stream.release()
        except:
            pass
        #self.cmd_feedback_thread.join()
        #self.vid_receive_thread.join()
        #self.push_thread.join()
        print(f"Disconnected from {self.ip}")
    
    def send(self,*args):
        '''Send commands directly! If there is multiple args it will join them with spaces.'''
        #assert(self.isOpen)
        cmdstring = ' '.join([str(a) for a in args])+';'
        self.ctrl_sock.sendall(cmdstring.encode('utf8'))
        #print(f'Sent: {cmdstring}')

    def __recvvideo(self):
        self.send('stream on')
        sleep(1)
        self.send('camera exposure small') #i saw this in their example code
        self.stream = cv2.VideoCapture(f'tcp://@{self.ip}:{VIDEO_PORT}')
        while not self.stream.isOpened(): sleep(0)
        #self.stream.set(cv2.CAP_PROP_FRAME_WIDTH,1920)
        #self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT,1080)
        while self.stream.isOpened() and self.isOpen: 
            _, self.frame = self.stream.read()
            self.hasNewFrame = True
        print("Video thread stopped!")

    def __recvmsg(self):
        while self.isOpen:
            raw = self.ctrl_sock.recv(1024)
            #print(f'Received: {raw.decode("utf-8")}')
        print("Feedback thread stopped!")

    def __recvpush(self):
        self.send('chassis push position on pfreq 5 attitude on afreq 5') #receive data 5Hz
        while self.isOpen:
            raw = self.ctrl_sock.recv(1024)
            data = raw.decode('utf-8').split(' ')
            if data[:3] == ['chassis','push','position']:
                self.pos[0],self.pos[1] = float(data[3]),float(data[4])
            elif data[:3] == ['chassis','push','attitude']:
                self.pos[2] = float(data[5])
        print("Push thread stopped!")


    ##################
    # ROBOT COMMANDS #
    ##################

    def move(self,x=.0,y=.0,wait=True,buffer=BUFFER_TIME,speed=SPD_LIMIT):
        '''
        Move robot in metres relative to current position (will move diagonally). Speed limit of 0.3m/s.
        - x (number, default: 0.0): distance in x axis to move in metres
        - y (number, default: 0.0): distance in y axis to move in metres
        - wait (bool, default: True): whether to wait for action to complete
        '''
        self.send('chassis','move','x',x,'y',y,'z',0.0,'vxy',min(speed,SPD_LIMIT))
        if wait: sleep(calculate_move_time(x,y,speed)+buffer)

    def speed(self,x=.0,y=.0,z=.0):
        '''
        Move robot at speed (% of 0.3m/s) (will move diagonally). Speed limit of 0.3m/s.
        - x (number, default: 0.0): between -100 to 100
        - y (number, default: 0.0): between -100 to 100
        '''
        self.send('chassis','speed','x',min(100.0,max(x,-100.0))/100.0*SPD_LIMIT,'y',min(100.0,max(y,-100.0))/100.0*SPD_LIMIT,'z',min(100.0,max(z,-100.0))/100.0*TURN_LIMIT) #doesnt account for diagonals properly
    def brake(self): self.move(buffer=0.0)

    def turn(self,ang,wait=True,buffer=BUFFER_TIME,speed=TURN_LIMIT):
        '''
        Rotate robot in degrees relative to current rotation. Speed limit of 10deg/s.
        - ang (number): angle to turn in degrees
        - wait (bool, default: True): whether to wait for action to complete
        '''
        self.send('chassis','move','z',ang,'vz',min(speed,TURN_LIMIT))
        if wait: sleep(calculate_turn_time(ang,speed)+buffer)

    def reset_origin(self):
        self.send('robotic_arm','move','x',-100,'y',-300)
        sleep(3)
        #transformation layer not necessary if arm motion is relative to this lowest position!

    def cam_doll(self):
        '''Move arm to position where camera is facing forwards'''
        self.send('robotic_arm','move','x',100,'y',40) #in cm
        #10,20
        sleep(1)
        #raise NotImplementedError

    def cam_ground(self):
        '''TODO: Move arm to position where camera is facing ground'''
        self.send('robotic_arm','move','x',210,'y',64) #in cm
        self.open_claw()
        sleep(1)
        #raise NotImplementedError

    def open_claw(self):
        self.send('robotic_gripper open 4')

    def close_claw(self):
        self.send('robotic_gripper close 2')

    def light_red(self):
        print("Blink Red!")
        self.send('led control comp bottom_all r 255 g 0 b 0 effect solid')
        sleep(1)
        self.send('led control comp bottom_all r 255 g 255 b 255 effect solid')

    def light_green(self):
        print("Blink Green!")
        self.send('led control comp bottom_all r 0 g 255 b 0 effect solid')
        sleep(1)
        self.send('led control comp bottom_all r 255 g 255 b 255 effect solid')

class PID():

    def __init__(self,tgt,p,i,d):
        self.kp = p
        self.ki = i
        self.kd = d
        self.tgt = tgt

        self.ep = 0.0
        self.ip = 0.0

    def update(self,x,dt):
        e = self.tgt - x
        self.ip += e*dt
        v = self.kp*e + self.ki*self.ip + self.kd*(e-self.ep)/dt
        self.ep = e
        return v

if __name__ == "__main__":
    #python -i robot.py
    with Robot('192.168.2.1') as robot:
        robot.reset_origin()
        robot.cam_doll()
        cv2.namedWindow('Livefeed', cv2.WINDOW_AUTOSIZE)
        while True:
            if not robot.hasNewFrame: continue
            robot.hasNewFrame = False
            cur_im = robot.frame.copy()
            cv2.imshow('Livefeed',cur_im)
            cv2.waitKey(1)
            if cv2.getWindowProperty('Livefeed',cv2.WND_PROP_VISIBLE) < 1: break
    cv2.destroyAllWindows()