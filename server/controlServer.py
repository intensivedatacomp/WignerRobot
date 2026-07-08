import json
import socket
from threading import Thread
import time

class ControlServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))

        self.client = None
        self.running = False
        self.thread = None

        self.server_socket.listen(1)
        print("Waiting for connection...")

    def close(self):
        self.running = False
        self.thread.join()
        self.server_socket.close()

    def start(self, Control, thread_sleep):
        self.running = True
        self.client, _ = self.server_socket.accept()
        self.thread = Thread(target=self.control_thread, args=(Control, thread_sleep))
        self.thread.start()

    def control_thread(self, Control, thread_sleep):
        while self.running:
            Control.time = time.time_ns()
            sendParams = {
                "shutdown": Control.shutdown,
                "speed": Control.speed,
                "angles": Control.angles,
                "us_measuring": Control.us_measuring,
                "time": Control.time,
                "buzzer": Control.buzzer
            }
            try:
                self.client.sendall((json.dumps(sendParams)).encode('utf-8'))
            except Exception as e:
                print(f"Error sending data: {e}")
                Control.shutdown = True
            Control.buzzer = ""
            time.sleep(thread_sleep)