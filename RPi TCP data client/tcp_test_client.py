import asyncio
import time
import random

async def client(message):

    reader, writer = await asyncio.open_connection(
        '127.0.0.1', 8888)

    writer.write(message.encode())
    await writer.drain()

    writer.close()
    await writer.wait_closed()

for i in range(200):
    asyncio.run(client(str(random.randint(-10,10))))
    time.sleep(0.2)
