import asyncio
TARGET_HOST = '127.0.0.1'
TARGET_PORT = 8200
LISTEN_HOST = '0.0.0.0'
LISTEN_PORT = 8210

async def pump(reader, writer):
    try:
        while not reader.at_eof():
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass

async def handle(client_reader, client_writer):
    try:
        server_reader, server_writer = await asyncio.open_connection(TARGET_HOST, TARGET_PORT)
    except Exception:
        client_writer.close()
        await client_writer.wait_closed()
        return
    await asyncio.gather(
        pump(client_reader, server_writer),
        pump(server_reader, client_writer),
    )

async def main():
    server = await asyncio.start_server(handle, LISTEN_HOST, LISTEN_PORT)
    async with server:
        await server.serve_forever()

asyncio.run(main())
