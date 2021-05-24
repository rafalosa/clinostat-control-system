import asyncio
import time
import random


async def client(message, address_, port_):

    reader, writer = await asyncio.open_connection(address_, port_)

    writer.write(message.encode())
    await writer.drain()

    writer.close()
    await writer.wait_closed()
    print("Sending data packet '{}' to: {}".format(msg, address + ":" + str(port)))

address = '127.0.0.1'
port = 8000

for i in range(200):
    msg = str(random.randint(-10,10))

    asyncio.run(client(msg,address,port))
    time.sleep(0.2)
