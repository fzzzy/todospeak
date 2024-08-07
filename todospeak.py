

import asyncio
from concurrent.futures import ThreadPoolExecutor
import json

from fastapi import FastAPI, Form
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    Response,
    StreamingResponse
)

import uuid

thread_pool = ThreadPoolExecutor()
convs = {}


app = FastAPI()


@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(
        content=open("index.html").read(),
        status_code=200
    )


@app.get("/favicon.ico")
async def favicon():
    return FileResponse("favicon.ico")


@app.get("/index.css")
async def serve_css():
    with open("index.css", "r") as file:
        content = file.read()
    return Response(content=content, media_type="text/css")


@app.get("/index.js")
async def serve_js():
    with open("index.js", "r") as file:
        content = file.read()
    return Response(content=content, media_type="application/javascript")


def get_next(gen):
    try:
        return gen.__next__()
    except StopIteration:
        return None


async def event_generator(q, initial=None):
    if initial is not None:
        jsondata = json.dumps(initial)
        yield f"data: {jsondata}\n\n"
    loop = asyncio.get_running_loop()
    while True:
        chat = await q.get()
        if chat is None:
            print("EXITING")
            break
        r = str(chat)
        gen = iter(r)
        while True:
            item = await loop.run_in_executor(thread_pool, get_next, gen)
            if item is None:
                yield 'data: {"finish_reason": "stop"}\n\n'
                #print("End Generate Tokens")
                break
            jsondata = json.dumps({"content": item})
            #print(jsondata)
            yield f"data: {jsondata}\n\n"
        #print(r)


@app.get("/conversation")
async def conversation():
    conv_id = str(uuid.uuid4())
    queue = asyncio.Queue()
    await queue.put({
        "prompt": "Hello",
        "system": "You are a helpful chat bot. Respond in markdown format. Keep responses brief."
    })
    convs[conv_id] = queue
    return StreamingResponse(
        event_generator(queue, initial={"id": conv_id}),
        media_type="text/event-stream"
    )


@app.post("/chat/{cid}")
async def chat(cid, text: str = Form(...)):
    await convs[cid].put({"prompt": text})
    return {}

