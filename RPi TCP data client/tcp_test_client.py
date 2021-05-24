import asyncio
import time

async def client(message, address_, port_):

    reader, writer = await asyncio.open_connection(address_, port_)

    writer.write(message.encode())
    await writer.drain()

    writer.close()
    await writer.wait_closed()


address = '127.0.0.1'
port = 8000

HEADER_SIZE = 10

with open("grav_data.csv","r") as file:

    for line in file:
        msg = f'{len(line):<{HEADER_SIZE}}' + line
        asyncio.run(client(msg,address,port))
        time.sleep(0.01)

