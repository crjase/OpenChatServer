import threading
import colorama
import platform
import socket
import time
import json
import os

from colorama import Fore
from datetime import date




def clear():
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")




class Server:
    def __init__(self, ip, port):
        # Chat History Data
        self.chatHistory = []
        
        # List of current connections
        self.connections = []
        
        # Prevents race conditions between threads
        self.lock = threading.Lock()
        
        # Connection Details
        self.ip = ip
        self.port = port
        self.hostName = ""

        # Socket Setup
        self.server_socket = None

        # Flag to stop the listening thread
        self.keep_listening = True

        # Initialize Colorama
        colorama.init()

        # Load account information from this file.
        with open("./accounts.json", "r") as f:
            self.accounts = json.load(f)


    # Handles account logins and grants access to the server
    def login_handler(self, connection, username, password):

        if not username or not password:
            self.remove_connection(connection)
            return False

        if username in self.accounts and self.accounts[username]["password"] == password:
            print(Fore.GREEN + f"User {username} has logged in." + Fore.RESET)
            return True
        else:
            print(Fore.RED + f"Invalid username or password. Failed attempt on user ({username})" + Fore.RESET)
            self.remove_connection(connection)
            return False


    def command_handler(self):

        # Check the lenngth of input
        def check_args_length(command, expected_length, min_length=None, max_length=None):
            if len(command) != expected_length:
                print(Fore.RED + f"Command '{command[0]}' expects {expected_length - 1} argument(s)." + Fore.RESET)
                return False

            if min_length is not None and len(command) < min_length:
                print(Fore.RED + f"Command '{command[0]}' expects at least {min_length - 1} argument(s)." + Fore.RESET)
                return False

            if max_length is not None and len(command) > max_length:
                print(Fore.RED + f"Command '{command[0]}' expects at most {max_length - 1} argument(s)." + Fore.RESET)
                return False
            return True


        # Define a function to handle the "exit" command
        def handle_exit():
            self.stop()
            return

        # Define a function to handle the "say" command
        def handle_say(command):

            # Remove the first arg so it's just a message
            del command[0]
            msg = ' '.join(command)

            self.broadcast(msg)
            self.chatHistory.append(msg)

        def handle_clearChat():
            self.chatHistory = []

        def handle_help():
            print (f"\n{Fore.CYAN}-------- List of Commands --------{Fore.RESET}\n")

            with open("./commands.txt", "r") as f:
                print(f.read())

            input(f"\n\n {Fore.CYAN}Press 'Enter' when you're finished reading...{Fore.RESET}")
            clear()


        # Get input from user and split into command and arguments
        command = input("\n\n> ").split()

        # Clear old logs
        clear()

        # Continue if nothing is entered
        if not command:
            return

        # Handle the command based on the first argument
        if command[0] == "exit":
            handle_exit()
        elif command[0] == "say":
            handle_say(command)
        elif command[0] == "clear":
            handle_clearChat()
        elif command[0] == "help":
            handle_help()
        else:
            print(Fore.RED + "Invalid command." + Fore.RESET)


    # Log chatHistory[] every _
    def log_chat(self):
        while self.keep_listening:
        
            # Wait 30 Minutes between each log
            minutes_delay = 30
            time.sleep(minutes_delay * 60) # convert minutes to seconds

            # Make sure there is a logs folder
            if not os.path.isdir("./logs"):
                os.makedirs("./logs")

            # Create a timestamp
            timestamp = date.today().strftime("%Y-%m-%w-%S")

            # Create a chatHistory log
            with open (f"./logs/log_{timestamp}.txt", "w") as f:
                f.write(str(self.chatHistory))



    def run_ui(self):

        # Server's Console UI
        while self.keep_listening:
            print("Server running. Type 'exit' to exit, and 'enter' to refresh logs.")
            print(f"{Fore.LIGHTBLACK_EX}Connected Users: {len(self.connections)}{Fore.RESET}\n")

            print(Fore.GREEN + ".=.=.=.= Chat Logs =.=.=.=." + Fore.RESET)
            for msg in self.chatHistory:
                print(msg)

            # Run the command logic
            self.command_handler()


    def stop(self):
        # Broadcast a stop message
        self.broadcast("Server has manually stopped.")

        # Set the flag to stop the listening thread
        self.keep_listening = False
        
        # Close all client connections
        with self.lock:
            for connection in self.connections:
                connection.close()
            self.connections = []
        
        # Close the server socket
        if self.server_socket:
            self.server_socket.close()
        
        print("Server stopped.")


    def bind(self):
        # Socket Setup
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.ip, self.port))
        
        print(Fore.CYAN + f"Server Bound To {self.ip}:{self.port}" + Fore.RESET)


    # Listens for incoming connections and setup all the stuff for each connection.
    def listen(self):
        self.server_socket.listen()

        # If this stops, all the other threads stop. (pretty much an entrypoint)
        while self.keep_listening:
            # Wait until a client connects and return a socket object for the client.
            # client_socket is a new socket object representing the connection to the client.
            # address is a tuple representing the IP address and port number of the client.
            client_socket, address = self.server_socket.accept()

            print(f"New connection from {address[0]}:{address[1]}")

            # Create a new thread for each client connection
            client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
            client_thread.start()
            
            # Append the client connection to the list
            self.connections.append(client_socket)


    # Sends the message to all incoming sockets, except the sender socket.
    def broadcast(self, message, sender_socket=None):

        # Find the socket that was passed as an argument
        for connection in self.connections:

            # Exclude the client sending the message if sender_socket is provided
            if sender_socket and connection == sender_socket:
                continue
            try:
                connection.send(message.encode('utf-8'))
            except:
                self.remove_connection(connection)


    # Ching Long Ming Bong
    def remove_connection(self, connection):
        # and threading.lock does what? (not my problem, just added it)
        with self.lock:
            if connection in self.connections:
                connection.close()
                self.connections.remove(connection)

                print(f"Disconection Occured (how sad)")


    # Handle all the client code.
    def handle_client(self, client_socket):

        # Request username
        client_socket.send(".=.=.=.=. Enter username .=.=.=.=.".encode())
        username = client_socket.recv(1024).decode().strip()

        # Request password
        client_socket.send(".=.=.=.=. Enter password .=.=.=.=. ".encode())
        password = client_socket.recv(1024).decode().strip()

        # Force the connection to have an account on the server
        login = self.login_handler(connection=client_socket, username=username, password=password)
        if login: client_socket.send("\n-----------------\nLogin successful.\n-----------------\n".encode())

        while self.keep_listening:
            try:
                message = client_socket.recv(1024).decode('utf-8')

                # WHY AREN'T YOU TALKIN' BOBBY!??
                if not message:
                    self.remove_connection(client_socket)
                    break

                self.chatHistory.append(message)
                self.broadcast(message, client_socket)

            # Remove any sussy buisness
            except:
                self.remove_connection(client_socket)
                break




if __name__ == "__main__":
    server = Server('0.0.0.0', 44444)

    # Bind server to local address
    server.bind()

    # Start the server's listen() method in a separate thread
    server_thread = threading.Thread(target=server.listen)
    server_thread.start()

    # Add some p'jazz with hot and sexy UI
    ui_thread = threading.Thread(target=server.run_ui)
    ui_thread.start()

    # Start the logging thread
    logging_thread = threading.Thread(target=server.log_chat)
    logging_thread.start()