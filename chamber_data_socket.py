import asyncio
import threading
from typing import Optional


class ServerThread(threading.Thread):

    def __init__(self,*args,**kwargs):
        threading.Thread.__init__(self,*args,**kwargs)
        self.running = False
        self.refresh_rate = 10

    def start(self) -> None:
        threading.Thread.start(self)
        self.running = True


class DataServer:

    def __init__(self,parent,console_link=None,plot_link=None,address="127.0.0.1",port=8888):
        self.server = None
        self.server_thread = None
        self.address = address
        self.port = port
        self.running = False
        self.parent = parent
        self.console = console_link
        self.fig = plot_link

    def runServer(self):
        self.server_thread = ServerThread(target=lambda: asyncio.run(self.mainServer(self.address,self.port)))
        self.server_thread.start()

    def close(self):
        self.console.println("Data server closed.".format(self.address, self.port), headline="TCP: ",
                             msg_type="TCP")
        self.running = False
        self.server.close()
        self.server_thread.join()

    def linkConsole(self,link):
        self.console = link

    def linkPlots(self,link):
        self.fig = link

    async def mainServer(self,address_,port_):
        # todo: Handle exceptions if server cannot be started. Print exception in console
        try:
            self.server = await asyncio.start_server(self.clientConnected,address_,port_)
            # "192.123.123.123"
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

        data = await reader.read(100)
        message = data.decode()

        self.console.println(f"{message!r}",headline="TCP: ",msg_type="TCP")

        # print(f"Send: {message!r}")
        # writer.write(data)
        # await writer.drain()
        # print("Close the connection")
        writer.close()



