import time
from threading import Thread

import RPi.GPIO as GPIO

class USSensor:

    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        self.US_TRIGGER = 9
        self.US_ECHO = 8

        GPIO.setup(self.US_TRIGGER, GPIO.OUT)
        GPIO.setup(self.US_ECHO, GPIO.IN)
        
        self.running = True
        self.thread = None

    def start(self, Control, thread_sleep=0.1):
        self.thread = Thread(target = self.control_thread, args = (Control, thread_sleep), daemon=True)
        self.thread.start()

    def control_thread(self, Control, thread_sleep=0.1):
        while self.running:
            if Control.us_measuring:
                Control.us_measurement = self.distance()
            time.sleep(thread_sleep)

    def distance(self):
        # 10us is the trigger signal
        GPIO.output(self.US_TRIGGER, GPIO.HIGH)
        time.sleep(0.00001)  #10us
        GPIO.output(self.US_TRIGGER, GPIO.LOW)
        t0 = time.time()
        while not GPIO.input(self.US_ECHO):
            if time.time() - t0 > 1:
                return -1
            time.sleep(0)
        t1 = time.monotonic_ns()
        while GPIO.input(self.US_ECHO):
            if time.time() - t0 > 10:
                return -1
            time.sleep(0)
        t2 = time.monotonic_ns()
        return ((t2 - t1) * 340 / 2 ) / 1000000000
    
    def __del__(self):
        self.running = False
        self.thread.join(timeout=1)
