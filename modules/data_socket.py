import socket
import threading


class DataServer:

    def __init__(self,address="127.0.0.1",port=8888):
        self.queues = []
        self.socket = None
        self.server_thread = None
        self.console = None
        self.running = False
        self.address = address
        self.port = port
        self.HEADER_SIZE = 10

    def runServer(self):
        try:
            self.socket = socket.create_server((self.address,self.port), family=socket.AF_INET)
        except OSError as err:
            self.console.println(err.args[1],headline="TCP ERROR: ",msg_type="ERROR")
            raise ServerStartupError(err.args[1])
        self.running = True
        self.server_thread = threading.Thread(target=self._serverLoop)
        self.server_thread.setDaemon(True)
        self.server_thread.start()

    def _serverLoop(self):

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

                    if not self.queues[1].empty():
                        response = str(self.queues[1].get())
                    else:
                        response = "default"
                    response = f"{len(response):<{self.HEADER_SIZE}}" + response
                    client.sendall(response.encode())

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
        # todo: Make 2 methods: attachReceiveQueue and attachResponseQueue, much clearer and universal.

        # todo: Or just make two queues that are attached to the server object at all times and just access them
        #  externally as app.data_server.containers["respond"] or app.data_server.containers["receive"]

    def linkConsole(self, link):  # todo: Convert to linkOutput(self, output, printer), which would include any possible
        self.console = link


class ServerStartupError(Exception):
    def __init__(self,msg):
        super().__init__()
        self.message = msg
