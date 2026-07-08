import time
from threading import Thread

import RPi.GPIO as GPIO

class Servo:

    def __init__(self):
        self.us_servo=5
        self.camera_horizontal = 7
        self.camera_vertical = 6
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        self.names = {
            "us" : self.us_servo,
            "camera_horizontal" : self.camera_horizontal,
            "camera_vertical" : self.camera_vertical
        }
        self.repeat = {
            "us" : 1,
            "camera_horizontal" : 1,
            "camera_vertical" : 1
        }

        GPIO.setup(self.camera_horizontal, GPIO.OUT)
        GPIO.setup(self.us_servo, GPIO.OUT)
        GPIO.setup(self.camera_vertical, GPIO.OUT)

        self.angles = [90, 90, 90]
        self.running = False
        self.thread = None
    
    def servoPulse(self, servoID, myangle):
        servoPin = self.names[servoID]
        pulsewidth = (myangle*11) + 500  # The pulse width
        irep = self.repeat[servoID]
        for i in range(irep) :
            GPIO.output(servoPin,GPIO.HIGH)
            t0 = time.monotonic_ns()
            while (time.monotonic_ns() - t0) < pulsewidth*1000:
                pass
            GPIO.output(servoPin,GPIO.LOW)
            time.sleep(0.1)
        
    def start(self, Control, thread_sleep=0.1):
        self.running = True
        self.thread = Thread(target=self.control_thread, args=(Control, thread_sleep))
        self.thread.start()

    def control_thread(self, Control, thread_sleep):
        while self.running:
            for i in range(3):
                if True: #self.angles[i] != Control.angles[i]:
                    self.servoPulse(list(self.names.keys())[i], Control.angles[i])
                    self.angles[i] = Control.angles[i]
            time.sleep(thread_sleep)

    
    def __del__(self):
        self.running = False
        if self.thread:
            self.thread.join()
        GPIO.cleanup()
