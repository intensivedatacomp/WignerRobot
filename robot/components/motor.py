from threading import Thread
import time

import RPi.GPIO as GPIO

class Motor:
    """
    The movements of the robot.
    """

    class Pin:
        def __init__(self, forward_pin, backward_pin, pwm_pin, frequency):
            self.forward_pin = forward_pin
            self.backward_pin = backward_pin
            self.frequency = frequency
            self.pwm_pin = pwm_pin

            GPIO.setup(self.forward_pin,GPIO.OUT)
            GPIO.setup(self.backward_pin,GPIO.OUT)
            GPIO.setup(self.pwm_pin,GPIO.OUT)

            self.pwm = GPIO.PWM(self.pwm_pin,self.frequency)
            self.pwm.start(0)


    def __init__(self, frequency=100):

        self.frequency = frequency

        GPIO.setwarnings(False)

        GPIO.setmode(GPIO.BCM)  # use BCM numbers

        self.motors = {
            "UL": self.Pin(21, 20, 0, self.frequency),
            "LL": self.Pin(22, 23, 1, self.frequency),
            "UR": self.Pin(24, 25, 12, self.frequency),
            "LR": self.Pin(27, 26, 13, self.frequency)
        }

        self.thread = None
        self.running = False


    def set_speed(self, speed):
        """
        Start the motors.

        Parameters
        ----------
        speed : list of float
            The first number sets the forward speed, the second sets the speed of the turning
        
        Examples
        --------
        >>> set_speed([75, 0])
        # Starts moving forward with a speed of 75 (the speed ranges from 0 to 100)

        >>> set_speed(0)
        # Stops the motion
        """

        if type(speed) is dict:
            mas = max(speed.values())/self.frequency
            mis = -min(speed.values())/self.frequency
            factor = max(mas, mis, 1)

            for name, pins in self.motors.items():
                sp = int(speed[name]/factor)
                #print(name, pins, sp)
                if sp > 0:
                    GPIO.output(pins.backward_pin, GPIO.LOW)
                    GPIO.output(pins.forward_pin, GPIO.HIGH)
                    pins.pwm.ChangeDutyCycle(sp)
                elif sp < 0:
                    GPIO.output(pins.forward_pin, GPIO.LOW)
                    GPIO.output(pins.backward_pin, GPIO.HIGH)
                    pins.pwm.ChangeDutyCycle(-sp)
                else:
                    GPIO.output(pins.forward_pin, GPIO.LOW)
                    GPIO.output(pins.backward_pin, GPIO.LOW)
                    pins.pwm.ChangeDutyCycle(0)

        elif type(speed) is list:
            if len(speed) != 2:
                raise ValueError("Speed list must have 2 elements")
            sp = {
                "UL": speed[0],
                "LL": speed[0],
                "UR": speed[1],
                "LR": speed[1]
            }
            self.set_speed(sp)

        elif type(speed) is int:
            sp = {
                "UL": speed,
                "LL": speed,
                "UR": speed,
                "LR": speed
            }
            self.set_speed(sp)

    def start(self, Control, thread_sleep=0.1):
        """
        Starts the control thread.
        """
        self.running = True
        self.speed = Control.speed
        self.set_speed(self.speed)
        self.thread = Thread(target = self.control_thread, args=(Control, thread_sleep))
        self.thread.start()

    def control_thread(self, Control, thread_sleep):
        while self.running:
            if self.speed != Control.speed:
                self.speed = Control.speed
                self.set_speed(self.speed)
            time.sleep(thread_sleep)
    
    def stop(self):
        if self.running:
            self.running = False
            try:
                self.thread.join()
            except:
                pass


    def __del__(self):
        """
        Stops the motion and cleans the GPIO ports.
        """
        self.running = False
        try:
            self.thread.join()
        except:
            pass
        self.set_speed(0)
        GPIO.cleanup()


            
if __name__ == "__main__":
    motors = Motor()

    speed = {
        "UL": 20,
        "LL": 20,
        "UR": 20,
        "LR": 20
    }

    motors.set_speed([0,100])

    time.sleep(1)
