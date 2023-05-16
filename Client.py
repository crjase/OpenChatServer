import socket
import threading

class Client:
    def __init__(self, ip, port):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ip = ip
        self.port = port
        
    def connect(self):
        self.client_socket.connect((self.ip, self.port))
        
        # Start a new thread to receive messages
        receive_thread = threading.Thread(target=self.receive)
        receive_thread.start()
        
        # Send messages from the console input
        while True:
            message = input()
            self.client_socket.send(message.encode('utf-8'))
            
    def receive(self):
        while True:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                print(message)
            except:
                self.client_socket.close()
                break
                

if __name__ == '__main__':
    client = Client('localhost', 44444)
    client.connect()