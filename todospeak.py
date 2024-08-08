
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
    global ALL_TOOLS_LIST
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
                "required": list(params.keys())
            }
        }
    }
    ALL_TOOLS[name] = result
    ALL_TOOLS_LIST.append(result['spec'])
    return result


add_list = tool(
    lambda name: print("add", name),
    "add_list",
    "Add a new todo list with a given name. The new todo list is automatically selected after creation.",
    {"name": ("string", "The name of the new todo list.")})


delete_list = tool(
    lambda index: print("delete", index),
    "delete_list",
    "Delete the todo list with the given index. Indices start at 1.",
    {"index": ("number", "The index of the todo list to delete. Indices start at 1.")})


list_lists = tool(
    lambda: print("list lists"),
    "list_lists",
    "List all the todo lists.")


select_list = tool(
    lambda index: print("select", index),
    "select_list",
    "Select a todo list with a given name, such that commands affecting todo items apply to the selected list.",
    {"index": ("number", "The index of the todo list to select. Indices start at 1.")})


read_list = tool(
    lambda: print("read list"),
    "read_list",
    "Return the contents of the selected todo list.",
    {})
    

add_todo = tool(
    lambda todo: print("add todo", todo),
    "add_todo",
    "Add a new todo item to the selected list.",
    {"todo": ("string", "The text of the todo.")})


delete_todo = tool(
    lambda index: print("del todo", index),
    "delete_todo",
    "Delete the numbered todo item from the selected list. Indices start at 1.",
    {"index": (
        "number",
        "The index of the todo to delete from the currently selected list.")})


read_todo = tool(
    lambda x: print("read todo", x),
    "read_todo",
    "Return the contents of the todo at the given index in the selected list. Indices start at 1.",
    {"todo": (
        "number",
        "The index of the todo to return.")})


do_not_understand = tool(
    lambda x: print("I don't understand", x),
    "do_not_understand",
    "If the user input does not seem to apply to any of the other tools, this tool must be used by default. The error parameter can be used to ask the user for clarification on their input.",
    {"error": (
        "string",
        "The message to show to the user asking for clarification on their request.")})


print(ALL_TOOLS_LIST)


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
        print("GOT CHAT", chat)
        if chat is None:
            print("EXITING")
            break
        if len(history) and history[-1]['role'] == "user":
            history[-1]['content'].append(
                {"type": "text", "text": chat["content"]})
        else:
            history.append(chat)
        result = await loop.run_in_executor(
            thread_pool,
            lambda: client.messages.create(
                #model="claude-3-5-sonnet-20240620",
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                tools=ALL_TOOLS_LIST,
                tool_choice={"type": "any"},
                messages=history))

        assistant_content = []
        for x in result.content:
            if x.type == "text":
                assistant_content.append({"type": "text", "text": x.text})
                jsondata = json.dumps({"content": x.text})
                yield f"data: {jsondata}\n\n"
            elif x.type == "tool_use":
                tool_id = x.id
                tool_name = x.name
                tool_input = x.input
                assistant_content.append({
                    "type": "tool_use",
                    "id": tool_id,
                    "name": tool_name,
                    "input": tool_input,
                })
                tool_output = ALL_TOOLS[tool_name]["tool"](**tool_input)
                history.append({
                    "role": "assistant",
                    "content": assistant_content})
                assistant_content = []
                history.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": str(tool_output)
                        }
                    ]
                })
                print(result)
                print("TOOL OUTPUT", tool_output)
                jsondata = json.dumps({
                    "content": f"using tool {tool_name}: {tool_output}"
                })
                yield f"data: {jsondata}\n\n"
                yield 'data: {"finish_reason": "stop"}\n\n'
        if len(assistant_content):
            history.append({"role": "assistant", "content": assistant_content})
        print("new history", history)
        yield 'data: {"finish_reason": "stop"}\n\n'


@app.get("/conversation")
async def conversation():
    conv_id = str(uuid.uuid4())
    queue = asyncio.Queue()
    # await queue.put({
    #     "role": "user",
    #     "content": "Hello"
    # })
    convs[conv_id] = queue
    return StreamingResponse(
        event_generator(queue, initial={"id": conv_id}),
        media_type="text/event-stream"
    )


@app.post("/chat/{cid}")
async def chat(cid, text: str = Form(...)):
    await convs[cid].put({"role": "user", "content": text})
    return {}

