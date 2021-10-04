import socket
import threading


class DataServer:

    def __init__(self,parent,thread_lock,address="127.0.0.1",port=8888):
        self.queues = []
        self.parent = parent
        self.socket = None
        self.server_thread = None
        self.console = None
        self.running = False
        self.address = address
        self.port = port
        self.HEADER_SIZE = 10
        self.lock = thread_lock


    def runServer(self):
        self.server_thread = threading.Thread(target=self._serverLoop)
        self.server_thread.setDaemon(True)
        self.server_thread.start()

    def _serverLoop(self):

        try:
            self.socket = socket.create_server((self.address,self.port), family=socket.AF_INET)
        except OSError as err:
            self.console.println(err.args[1],headline="TCP ERROR: ",msg_type="ERROR")
            return

        self.lock.acquire()
        self.console.println(f"Successfully connected to: {self.address}", headline="TCP: ", msg_type="TCP")
        self.parent.control_system.data_embed.enableInterface()
        self.running = True
        self.lock.release()
        self.socket.listen()

        if self.queues:

            while self.running:

                try:
                    client, address = self.socket.accept()
                except(socket.timeout, OSError):
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

                self.queues[0].put(message)
                # respond with current lighting setting

    def closeServer(self):
        self.running = False
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        finally:
            self.socket.close()

        self.socket = None

    def addQueue(self, q):
        self.queues.append(q)

    def linkConsole(self, link):
        self.console = link
