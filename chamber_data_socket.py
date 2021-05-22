import asyncio


class DataServer:

    def __init__(self,parent,address="127.0.0.1",port=8888):
        self.server = None
        self.parent = parent
        pass

    def runServer(self):
        asyncio.run(self.mainServer())

    def close(self):
        self.server.close()

    async def mainServer(self,address_="127.0.0.1",port_=8888):
        self.server = await asyncio.start_server(self.clientConnected,address_,port_)

        #addr = self.server.sockets[0].getsockname()
        #print(f'Serving on {addr}')
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



