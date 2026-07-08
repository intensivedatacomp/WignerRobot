import socket

class ControlClient:
    def __init__(self, host, port, timeout=1.0):
        self.host = host
        self.port = port
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.settimeout(timeout)
        try:
            self.client_socket.connect((self.host, self.port))
        except socket.error as e:
            print(f"Error connecting to control server: {e}")
            print(f"Host: {host}, Port: {port}")
        
    def getData(self):
        try:
            data = self.client_socket.recv(1024).decode('utf-8')
            return data
        except socket.timeout:
            print("Socket timeout occurred while waiting for data.")
            return None
        except socket.error as e:
            print(f"Socket error occurred: {e}")
            return None
    
    def close(self):
        self.client_socket.close()
        