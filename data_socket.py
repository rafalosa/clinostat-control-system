import socket
import threading
import os


class DataServer:

    def __init__(self,parent,thread_lock,queue_,address="127.0.0.1",port=8888):
        self.parent = parent
        self.socket = None
        self.server_thread = None
        self.console = None
        self.running = False
        self.address = address
        self.port = port
        self.HEADER_SIZE = 10
        self.lock = thread_lock
        self.data_queue = queue_

    def runServer(self):
        self.lock.acquire()
        self.parent.control_system.data_embed.enableInterface()
        self.running = True
        self.lock.release()
        self.server_thread = threading.Thread(target=self._serverLoop)
        self.server_thread.setDaemon(True)
        self.server_thread.start()

    def _serverLoop(self):
        self.socket = socket.create_server((self.address,self.port), family=socket.AF_INET)
        self.socket.listen()

        while self.running:

            try:
                client, address = self.socket.accept()
            except(socket.timeout,OSError):
                return
            finally:
                if not self.running:
                    return

            with client:
                fresh = True
                message = ''
                while True:
                    data = client.recv(16)
                    data = data.decode('utf-8')

                    if fresh:
                        message_len = int(data[:self.HEADER_SIZE])
                        fresh = False
                        message += data[self.HEADER_SIZE:]

                    else:
                        message += data

                    if len(message) == message_len:
                        break

            self.data_queue.put(message)

    def closeServer(self):
        self.running = False
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()
        self.socket = None

    def linkConsole(self,link):
        self.console = link


# todo: Add data client as a different class, no point in making a separate file for this.
