import asyncio
import threading


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
        self.server = None
        self.parent = parent
        self.server_thread = ServerThread(target=lambda: asyncio.run(self.mainServer()))

    def runServer(self):
        self.server_thread.start()

    def close(self):
        self.server.close()
        self.server_thread.join()

    async def mainServer(self,address_="127.0.0.1",port_=8888):
        self.server = await asyncio.start_server(self.clientConnected,address_,port_)

        async with self.server:
            try:
                await self.server.serve_forever()
            except asyncio.exceptions.CancelledError:
                pass

    async def clientConnected(self,reader,writer):
        data = await reader.read(100)
        message = data.decode()
        addr = writer.get_extra_info('peername')

        print(f"Received {message!r} from {addr!r}")
        self.parent.serial_config.console.println(f"{message!r}")

        print(f"Send: {message!r}")
        writer.write(data)
        await writer.drain()

        print("Close the connection")
        writer.close()



