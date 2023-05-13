#!/usr/bin/env python3

"""
# A simple instagram bot package to test uploading memes from a folder :welp:
"""

import io
import json
import asyncio
import aiohttp
import threading
from aiohttp import web
from pathlib import Path

from instagrapi import Client, exceptions
from threadsafe_shell import get_shell, Shell

import src.config as config
from src.bot_standalone import Bot as StandaloneBot



# INCOMING MESSAGE HANDLING


message_handlers = {}
def __add_websocket_handler_decorator(name:str = None):
    """ Decorator to add a function as a message handler """
    if name is None: raise ValueError("Websocket handler must provide a name!")
    def wrapper(func):
        message_handlers[name] = func
        return func
    return wrapper
def add_websocket_handler(name:str = None, function = None):
    if name is None: raise ValueError("Websocket handler must provide a name!")
    if function is None: raise ValueError("Websocket handler must provide a function!")
    message_handlers[name] = func


async def __process_message(ws, msg):
    data, _ = json.loads(msg.data)
    func = message_handlers.get(data['method'])
    await func(ws, data)


active_socks = {}
async def websocket_handler(request):
    try:
        # open connection
        ws = aiohttp.web.WebSocketResponse()
        await ws.prepare(request)
        ws_id = hash(ws)
        active_socks[ws_id] = ws
        if config.OUTPUT_TO_CONSOLE: print(f'Connection with {request.remote} opened, hash ID {ws_id}')
        # parse messages
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                await __process_message(ws, msg)
            elif msg.type == aiohttp.WSMsgType.ERROR:
                raise IOError(f'Connection closed with exception {ws.exception()}')
        # close connection
        if config.OUTPUT_TO_CONSOLE: print(f'Connection with {request.remote} closed')
    except asyncio.CancelledError:
        if config.OUTPUT_TO_CONSOLE: print(f'Connection with {request.remote} cancelled')
        await ws.close()
        ws = None
    except Exception as e:
        print(e)
        await ws.close(code=aiohttp.WSCloseCode.INTERNAL_ERROR)
        ws = None
    finally:
        del active_socks[ws_id]
    return ws

async def on_server_close(app):
    for id,sock in active_socks.items():
        await ws.close(code=aiohttp.WSCloseCode.GOING_AWAY, message='Server shutdown')



# WEBSERVER DEFINITION


# Request Routing
async def index(request: web.Request) -> web.Response:
    text = Path('src/webserver/index.html').read_text()
    return web.Response(text=text, content_type='text/html')

class WebserverFile(io.StringIO):
    def __init__(self, port:int = 5000):
        super().__init__()
        # server setup
        __app = web.Application()
        __app.on_shutdown.append(on_server_close)
        __app.router.add_static('/resources/', path='src/webserver/resources/', name='resources')
        __app.router.add_get('/ws/app/', websocket_handler)
        __app.router.add_get('/{tail:.*}', index)
        self.__server_runner = web.AppRunner(__app)
        # server thread
        self.port = port
        self.is_running = False
        self.__event_loop = None
        self.get_run_thread().start()
    
    def __run_thread_func(self):
        if config.OUTPUT_TO_CONSOLE: print("Starting webserver...")
        # setup event loop
        self.__event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.__event_loop)
        # initialize server
        self.__event_loop.run_until_complete(self.__server_runner.setup())
        # run server
        site = web.TCPSite(self.__server_runner, '0.0.0.0', self.port)
        self.__event_loop.run_until_complete(site.start())
        print("Started server.")
        self.is_running = True
        self.__event_loop.run_forever()
        self.is_running = False
    
    def get_run_thread(self):
        try:
            return self.__run_thread
        except AttributeError:
            self.__run_thread = threading.Thread(target=self.__run_thread_func, name="WebServerController-Daemon", daemon=True)
            return self.__run_thread
    
    def write(self, s: str, /) -> int:
        """ Writes a string to all open websockets. Returns the number of websockets written to. """
        if s == '': return 0
        i = 0
        s = s.replace("\033[30m", "</span><span class='colored color_black'>")\
             .replace("\033[31m", "</span><span class='colored color_red'>")\
             .replace("\033[32m", "</span><span class='colored color_green'>")\
             .replace("\033[33m", "</span><span class='colored color_yellow'>")\
             .replace("\033[34m", "</span><span class='colored color_blue'>")\
             .replace("\033[35m", "</span><span class='colored color_purple'>")\
             .replace("\033[36m", "</span><span class='colored color_cyan'>")\
             .replace("\033[37m", "</span><span class='colored color_white'>")\
             .replace("\033[0m",  "</span><span>")
        if self.is_running:
            for wsid,socket in active_socks.items():
                if not socket.closed:
                    task = socket.send_json({
                        'method': 'write',
                        'data': s
                    })
                    i += 1
                    asyncio.run_coroutine_threadsafe(task, self.__event_loop)
        return i
    
    def read(self, *args, **kwargs) -> int:
        raise IOError("This stream cannot be read from!")
    def readlines(self, *args, **kwargs) -> int:
        raise IOError("This stream cannot be read from!")


class Bot(StandaloneBot):
    def __init__(self, shell:Shell=None, client:Client=None):
        super().__init__(shell, client)
        self.__webserver = WebserverFile(port=5000)
        self.shell.set_log_output_file(self.__webserver)



# HANDLERS


@__add_websocket_handler_decorator(name="read")
async def __handle_read(ws, data):
    # print("got read signal!")
    pass


@__add_websocket_handler_decorator(name="write")
async def __handle_write(ws, data):
    # print("got write signal!")
    pass
