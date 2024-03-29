import queue
import socket
import threading
from typing import Callable


class DataServer:

    def __init__(self, address="127.0.0.1", port=8888):
        self.socket = None
        self.server_thread = None
        self.notify = None
        self.running = False
        self.address = address
        self.port = port
        self.HEADER_SIZE = 10
        self._containers = {}

    def run_server(self) -> None:
        try:
            self.socket = socket.create_server((self.address, self.port), family=socket.AF_INET)
        except OSError as err:
            if self.notify:
                self.notify(err.args[1], headline="TCP ERROR: ", msg_type="ERROR")
            raise ServerStartupError(err.args[1])
        self.running = True
        if self.notify:
            self.notify(f"Successfully connected to: {self.address}", headline="TCP: ", msg_type="TCP")
        self.server_thread = threading.Thread(target=self._server_loop)
        self.server_thread.start()

    def _server_loop(self) -> None:

        self.socket.listen()

        if self._containers["response"]:

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

                    self._containers["receive"].put(message)

                    if self._containers["response"]:
                        if not self._containers["response"].empty():
                            response = str(self._containers["response"].get())
                            self._containers["response"].task_done()
                        else:
                            response = "default"
                        response = f"{len(response):<{self.HEADER_SIZE}}" + response
                        client.sendall(response.encode())
        else:
            raise RuntimeError("Receiving queue must be attached. Use the attachReceiveQueue method.")

    def close_server(self) -> None:
        self.running = False
        close_failed = False

        try:
            self.socket.shutdown(socket.SHUT_RDWR)

        except OSError:
            close_failed = True

        finally:

            if not close_failed and self.notify:
                self.notify("Connection to server closed.", headline="TCP: ", msg_type="TCP")

            self.socket.close()
            self.socket = None

    def link_output(self, link: Callable) -> None:
        self.notify = link

    def attach_receive_queue(self, queue_: queue.Queue) -> None:
        self._containers["receive"] = queue_

    def attach_response_queue(self, queue_: queue.Queue) -> None:
        self._containers["response"] = queue_


class ServerStartupError(Exception):
    def __init__(self, msg):
        super().__init__()
        self.message = msg
