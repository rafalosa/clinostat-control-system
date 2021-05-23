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
        self.data_buffer_globe = None
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

    def linkDataBuffers(self,globe_link,grav_link):
        self.data_buffer_globe = globe_link
        self.data_buffer_grav = grav_link

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
        print(message)
        message = int(message)
        #self.console.println(f"{message!r}",headline="TCP: ",msg_type="TCP")
        self.data_buffer_globe.append(message)  # todo: Also save new data to file.
        self.parent.control_system.data_embed.new_data_available = True  # Ideally I would update the plots from here
        # but cross threaded calls to FigureCanvasTkAgg.draw() caused silent crashes and have to be handled by MainThread

        # todo: Scroll records, so they match the data buffer size.

        #print(np.arange(0, len(self.data_buffer)),self.data_buffer)
        #self.lines.plot(np.arange(0, len(self.data_buffer)),self.data_buffer)
        #self.lines.set_xdata(np.arange(0, len(self.data_buffer)))
        #self.lines.set_ydata(self.data_buffer)
        #self.canv.draw()
        # print(f"Send: {message!r}")
        # writer.write(data)
        # await writer.drain()
        # print("Close the connection")
        writer.close()



