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

means = [0,0,0]

with open("grav_data.csv","r") as file:

    for index,line in enumerate(file):

        values = [float(val) for val in line.split(";")]
        temp = [means[ind] * index / (index + 1) + values[ind] / (index + 1) for ind in range(3)]
        means = temp
        vals = values + means
        msg = ";".join([str(val) for val in vals])
        msg = f'{len(msg):<{HEADER_SIZE}}' + msg
        asyncio.run(client(msg,address,port))
        time.sleep(0.01)

