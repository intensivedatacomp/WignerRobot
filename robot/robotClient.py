import json
import socket
from videoClient import VideoClient
import sys

sys.path.append('./robot/components')
sys.path.append('./robot')

from buzzer import Buzzer
from motor import Motor
from servo import Servo
from usSensor import USSensor
from controlClient import ControlClient

from control import Control

with open('settings.json') as f:
    settings = json.load(f)

print("Starting video client")
print(f"Port: {settings['VIDEO_PORT']}")
video_client = VideoClient(
    target_host=settings["HOST_IP"],
    port=settings["VIDEO_PORT"],
    width=settings["IMAGE_WIDTH"],
    height=settings["IMAGE_HEIGHT"],
    fps=settings["FPS"],
)

video_client.start()

print("Starting hardware components")
motor = Motor()
motor.start(Control, settings["THREAD_SLEEP"])
    
servo = Servo()
servo.start(Control, settings["THREAD_SLEEP"])

us_sensor = USSensor()
us_sensor.start(Control, settings["THREAD_SLEEP"])

buzzer = Buzzer()
buzzer.start(settings["THREAD_SLEEP"])

print("Starting control client")
control_client = ControlClient(settings["HOST_IP"], settings["CONTROL_PORT"], settings["TIMEOUT_TIME"])

while not Control.shutdown:
    try:
        data = control_client.getData()
    except socket.timeout:
        print("Control signal timeout - Shutdown")
        Control.shutdown = True        
    if data:
        try:
            params = json.loads(data)
            print(params)
            Control.shutdown = params["shutdown"]
            Control.speed = params["speed"]
            Control.angles = params["angles"]
            Control.us_measuring = params["us_measuring"]
            Control.time = params["time"]
            if params["buzzer"] != "":
                buzzer.play(params["buzzer"])
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON data: {e}")
    else: 
        Control.shutdown = True
        print("Error: No data recieved")
        break


print("Shutting down control client")
try:
    control_client.close()
except Exception as e:
    print(f"Error closing control client: {e}")

print("Shutting down video client")
video_client.stop()


print("Stopping hardware components")
del motor
del servo
del buzzer
del us_sensor
exit(0)
