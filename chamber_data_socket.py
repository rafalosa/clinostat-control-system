import asyncio
import threading
import numpy as np


class ServerThread(threading.Thread):

    def __init__(self,*args,**kwargs):
        threading.Thread.__init__(self,*args,**kwargs)
        self.running = False
        self.refresh_rate = 10

    def start(self) -> None:
        threading.Thread.start(self)
        self.running = True


class DataServer:

    def __init__(self,parent,address="127.0.0.1",port=8888):
        self.parent = parent
        self.server = None
        self.server_thread = None
        self.console = None
        self.data_buffer_grav = None
        self.running = False
        self.address = address
        self.port = port

    def runServer(self):
        self.server_thread = ServerThread(target=lambda: asyncio.run(self.mainServer(self.address,self.port)))
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
        self.parent.control_system.data_embed.enableInterface()  # I dont like calling this from here, but I can't find
        # another solution as of now. It enables the whole embedded data interface if server setup was successful.

        async with self.server:
            try:
                await self.server.serve_forever()
            except asyncio.exceptions.CancelledError:
                pass

    async def clientConnected(self,reader,writer):
        # Incoming message format:
        # msg_type/msg_size/msg_data
        # msg_type = b'\x01' - handshake/ping, b'\x02' - streaming data

        # Return message, always 1 byte:
        # b'\x01' - handshake confirmation, b'\x02' - data received, continue
        # streaming data, b'\x03' - data received, stop sending data

        data = await reader.read(2)
        message = data.decode()
        message = int(message)
        data_buff = self.parent.control_system.data_embed.data_buffer_grav
        if len(data_buff) >= 100:
            data_buff = list(np.roll(data_buff,-1))
            data_buff[-1] = message
            # self.parent.control_system.data_embed.data_buffer_globe = data_buff
            self.parent.control_system.data_embed.data_buffer_grav = data_buff
        else:
            # self.parent.control_system.data_embed.data_buffer_globe.append(message)
            self.parent.control_system.data_embed.data_buffer_grav.append(message)  # todo: Also save new data to file.

        self.parent.control_system.data_embed.new_data_available = True  # Ideally I would update the plots from here
        # but cross thread calls to FigureCanvasTkAgg.draw() cause silent crashes and have to be handled by MainThread.

        # todo: Scroll records, so they match the data buffer size.

        # print(f"Send: {message!r}")
        # writer.write(data)
        # await writer.drain()
        # print("Close the connection")
        writer.close()


def decodePacket(packet):
    pass
