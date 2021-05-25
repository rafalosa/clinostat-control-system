import asyncio
import threading


class DataServer:

    def __init__(self,parent,thread_lock,queue_,address="127.0.0.1",port=8888):
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
        self.data_queue = queue_

    def runServer(self):
        self.server_thread = threading.Thread(target=lambda: asyncio.run(self.mainServer(self.address,self.port)))
        self.server_thread.start()

    async def closeFlag(self,fut):

        self.server.close()
        await self.server.wait_closed()
        fut.set_result(True)

    async def closeSetup(self):
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        loop.create_task(self.closeFlag(fut))
        if await fut:
            self.running = False

    def close(self):
        asyncio.run(self.closeSetup())

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

        try:
            await self.server.serve_forever()
        except asyncio.exceptions.CancelledError:
            pass

        while self.running:
            pass

        self.console.println("Data server closed.".format(self.address, self.port), headline="TCP: ",
                             msg_type="TCP")

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
                # message_len = int(data[:self.HEADER_SIZE])
                fresh = False
                message += data[self.HEADER_SIZE:]

            else:
                message += data

        #values = [float(val) for val in message.split(";")]
        self.data_queue.put(message)

        writer.close()

# todo: Add data client as a different class, no point in making a separate file for this.
