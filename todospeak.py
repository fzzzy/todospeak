
import anthropic

import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import functools

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


ALL_TOOLS = {}
ALL_TOOLS_LIST = []


def tool(tool_func, name, desc, params={}):
    """params example: {
        "location": (type, description)
    }
    """
    global ALL_TOOLS
    schema = {
        k: {"type": t, "description": d}
        for (k, (t, d)) in params.items()
    }
    result = {
        "tool": tool_func,
        "spec": {
            "name": name,
            "description": desc,
            "input_schema": {
                "type": "object",
                "properties": schema,
                "required": params.keys()
            }
        }
    }
    ALL_TOOLS[name] = result
    ALL_TOOLS_LIST.append(result['spec'])
    return result


add_list = tool(
    lambda x: print("add", x),
    "add_list",
    "Add a new todo list with a given name. The new todo list is automatically selected after creation.",
    {"name": ("string", "The name of the new todo list.")})


delete_list = tool(
    lambda x: print("delete", x),
    "delete_list",
    "Delete the todo list with the given name.",
    {"name": ("string", "The name of the todo list to delete.")})


select_list = tool(
    lambda x: print("select", x),
    "select_list",
    "Select a todo list with a given name, such that commands affecting todo items apply to the selected list.",
    {"name": ("string", "The name of the todo list to select.")})


read_list = tool(
    lambda: print("read list"),
    "read_list",
    "Return the contents of the selected todo list.",
    {})
    

add_todo = tool(
    lambda x: print("add todo", x),
    "add_todo",
    "Add a new todo item to the selected list.",
    {"todo": ("string", "The text of the todo.")})


delete_todo = tool(
    lambda x: print("del todo", x),
    "delete_todo",
    "Delete the numbered todo item from the selected list. Indexes start at 1.",
    {"todo": (
        "integer",
        "The index of the todo to delete from the currently selected list.")})


read_todo = tool(
    lambda x: print("read todo", x),
    "read_todo",
    "Return the contents of the todo at the given index in the selected list. Indexes start at 1.",
    {"todo": (
        "integer",
        "The index of the todo to return.")})


do_not_understand = tool(
    lambda x: print("I don't understand", x),
    "do_not_understand",
    "If the user input does not seem to apply to any of the other tools, this tool must be used by default. The error parameter can be used to ask the user for clarification on their input.",
    {"error": (
        "error",
        "The message to show to the user asking for clarification on their request.")})


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
    client = anthropic.Anthropic()
    history = []
    if initial is not None:
        jsondata = json.dumps(initial)
        yield f"data: {jsondata}\n\n"
    loop = asyncio.get_running_loop()
    while True:
        chat = await q.get()
        if chat is None:
            print("EXITING")
            break
        history.append(chat)
        result = await loop.run_in_executor(
            thread_pool,
            lambda: client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=1024,
                messages=history))
        #print(dict(result))
        assistant_content = []
        for x in result.content:
            if x.type == "text":
                assistant_content.append({"type": "text", "text": x.text})
                jsondata = json.dumps({"content": x.text})
                yield f"data: {jsondata}\n\n"
        history.append({"role": "assistant", "content": assistant_content})
        print("new history", history)


@app.get("/conversation")
async def conversation():
    conv_id = str(uuid.uuid4())
    queue = asyncio.Queue()
    await queue.put({
        "role": "user",
        "content": "Hello"
    })
    convs[conv_id] = queue
    return StreamingResponse(
        event_generator(queue, initial={"id": conv_id}),
        media_type="text/event-stream"
    )


@app.post("/chat/{cid}")
async def chat(cid, text: str = Form(...)):
    await convs[cid].put({"role": "user", "content": text})
    return {}

