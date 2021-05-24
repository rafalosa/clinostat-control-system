import asyncio
import threading
import numpy as np


class DataServer:  # todo: This class could probably inherit from threading.Thread

    def __init__(self,parent,thread_lock,address="127.0.0.1",port=8888):
        self.parent = parent
        self.server = None
        self.server_thread = None
        self.console = None
        self.data_buffer_grav = None
        self.running = False
        self.address = address
        self.port = port
        self.HEADER_SIZE = 10
        self.lock = thread_lock

    def runServer(self):
        self.server_thread = threading.Thread(target=lambda: asyncio.run(self.mainServer(self.address,self.port)))
        self.server_thread.start()

    def close(self):
        self.running = False
        self.server.close()
        self.server_thread.join()
        self.console.println("Data server closed.".format(self.address, self.port), headline="TCP: ",
                             msg_type="TCP")

    def linkConsole(self,link):
        self.console = link

    async def mainServer(self,address_,port_):

        try:
            self.server = await asyncio.start_server(self.clientConnected,address_,port_)

        except OSError as err:
            self.console.println(err.args[1], headline="TCP ERROR: ",
                                 msg_type="ERROR")
            return

        self.running = True
        self.console.println("Data server running on {}:{}.".format(address_, port_), headline="TCP: ",
                             msg_type="TCP")
        self.lock.acquire()
        self.parent.control_system.data_embed.enableInterface()  # I dont like calling this from here, but I can't find
        # another solution as of now. It enables the whole embedded data interface if server setup was successful.
        self.lock.release()
        async with self.server:
            try:
                await self.server.serve_forever()
            except asyncio.exceptions.CancelledError:
                pass

    async def clientConnected(self,reader,writer):
        # Incoming message format:
        # header (10 bytes) which includes message size/rest of message
        # rest of message = msg_type (1 byte)/msg_data (message size - 1 bytes)
        # msg_type = b'\x01' - handshake/ping, b'\x02' - streaming data

        # Return message, always 1 byte:
        # b'\x01' - handshake confirmation, b'\x02' - data received, continue
        # streaming data, b'\x03' - data received, stop sending data

        fresh = True

        message = ''

        while not reader.at_eof():

            data = await reader.read(16)
            data = data.decode('utf-8')

            if fresh:
                message_len = int(data[:self.HEADER_SIZE])
                fresh = False
                message += data[self.HEADER_SIZE:]

            else:
                message += data

        values = [float(val) for val in message.split(";")]

        self.lock.acquire()

        for index,buffer in enumerate(self.parent.control_system.data_embed.data_buffers):

            if len(buffer) >= 100:
                buffer = list(np.roll(buffer,-1))
                buffer[-1] = values[index]
                self.parent.control_system.data_embed.data_buffers[index] = buffer
                # todo: Consider using Queue to send new data.
            else:
                buffer.append(values[index])

            # todo: Also save new data to file.

        self.parent.control_system.data_embed.new_data_available = True

        self.lock.release()

        writer.close()


def rollData(buffer):
    pass

