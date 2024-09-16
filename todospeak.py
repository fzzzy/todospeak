

import anthropic

import asyncio
from concurrent.futures import ThreadPoolExecutor
import json

from fastapi import FastAPI, Form
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    RedirectResponse,
    Response,
    StreamingResponse
)

import uuid

import todoaccounts
import todostore

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

def add_list_glue(db, name):
    db.add_list(name)
    return {"text": f"List added. Lists:\n\n{list_lists_glue(db)['text']}\nSelected list: {name}\n"}

add_list = tool(
    add_list_glue,
    "add_list",
    "Add a new todo list with a given name. The new todo list is automatically selected after creation.",
    {"name": ("string", "The name of the new todo list.")})

def delete_list_glue(db, index):
    if db.del_list(index):
        return {"text": "List deleted."}
    return {"text": "List not found."}

delete_list = tool(
    delete_list_glue,
    "delete_list",
    "Delete the todo list with the given index. Indices start at 1.",
    {"index": ("number", "The index of the todo list to delete. Indices start at 1.")})

def list_lists_glue(db):
    result = ""
    for i, item in enumerate(db.list_lists()):
        result += f"{i + 1}. {item[1]}\n"
    return {"text": result}

list_lists = tool(
    list_lists_glue,
    "list_lists",
    "List all the todo lists.")

def select_list_glue(db, index):
    todos = db.select_list(index)
    result = f"List {todos.name} selected.\n\n"
    result += read_list_glue(db)["text"]
    return {"text": result}

select_list = tool(
    select_list_glue,
    "select_list",
    "Select a todo list with a given name, such that commands affecting todo items apply to the selected list.",
    {"index": ("number", "The index of the todo list to select. Indices start at 1.")})

def read_list_glue(db):
    result = ""
    todos = db.select_list(db.selected_list)
    for i, item in enumerate(todos.read_all()):
        result += f"{i + 1}. {item[1]}\n"
    return {"text": result}

read_list = tool(
    read_list_glue,
    "read_list",
    "Return the contents of the selected todo list.",
    {})

def read_complete_glue(db):
    result = ""
    todos = db.select_list(db.selected_list)
    for i, item in enumerate(todos.read_complete()):
        result += f"{i + 1}. {item[1]}\n"
    return {"text": result}

read_complete = tool(
    read_complete_glue,
    "read_complete",
    "Return the completed items of the selected todo list.",
    {})

def add_todo_glue(db, todo):
    todos = db.select_list(db.selected_list)
    todos.add_todo(todo)
    return {"text": f"Added to {todos.name} list."}

add_todo = tool(
    add_todo_glue,
    "add_todo",
    "Add a new todo item to the selected list.",
    {"todo": ("string", "The text of the todo.")})

def delete_todo_glue(db, index):
    todos = db.select_list(db.selected_list)
    if todos.del_todo(index):
        return {"text": "Deleted."}
    else:
        return {"text": "Todo not found."}

delete_todo = tool(
    delete_todo_glue,
    "delete_todo",
    "Delete the numbered todo item from the selected list. Indices start at 1.",
    {"index": (
        "number",
        "The index of the todo to delete from the currently selected list.")})

def mark_complete_glue(db, index):
    todos = db.select_list(db.selected_list)
    todos.mark_complete(index)
    return {"text": f"Marked complete. Completed items:\n\n{read_complete_glue(db)['text']}"}

mark_complete = tool(
    mark_complete_glue,
    "mark_complete",
    "Mark the numbered todo item from the selected list as complete. Indices start at 1.",
    {"index": (
        "number",
        "The index of the todo to mark as complete from the currently selected list.")})

def mark_incomplete_glue(db, index):
    todos = db.select_list(db.selected_list)
    todos.mark_incomplete(index)
    return {"text": f"Marked incomplete. Incomplete items:\n\n{read_list_glue(db)['text']}"}

mark_incomplete = tool(
    mark_incomplete_glue,
    "mark_incomplete",
    "Mark the numbered todo item from the selected list as incomplete. Indices start at 1.",
    {"index": (
        "number",
        "The index of the todo to mark as incomplete from the currently selected list.")})

do_not_understand = tool(
    lambda _db, error: {"text": f"I don't understand. {error}"},
    "do_not_understand",
    "If the user input does not seem to apply to any of the other tools, this tool must be used by default. The error parameter can be used to ask the user for clarification on their input.",
    {"error": (
        "string",
        "The message to show to the user asking for clarification on their request.")})
# print(ALL_TOOLS_LIST)


@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(
        content=open("index.html").read(),
        status_code=200
    )


@app.get("/favicon.ico")
async def favicon():
    return FileResponse("favicon.ico")


@app.get("/account.css")
async def serve_css():
    with open("account.css", "r") as file:
        content = file.read()
    return Response(content=content, media_type="text/css")


@app.get("/account.js")
async def serve_js():
    with open("account.js", "r") as file:
        content = file.read()
    return Response(content=content, media_type="application/javascript")


@app.get("/help.js")
async def serve_help():
    with open("help.js", "r") as file:
        content = file.read()
    return Response(content=content, media_type="application/javascript")


@app.post("/account")
async def create_account(name: str = Form(...)):
    a = todoaccounts.Accounts()
    user_id = str(uuid.uuid4())
    if a.add_account(name, user_id):
        print(f"Account created for: {name} {uuid}")
    return RedirectResponse(url=f"/account/{user_id}/", status_code=303)


@app.get("/account/{account_id}/")
async def render_account(account_id: str):
    return HTMLResponse(
        content=open("account.html").read(),
        status_code=200
    )


def get_next(gen):
    try:
        return gen.__next__()
    except StopIteration:
        return None


async def event_generator(db, q, account, initial=None):
    loop = asyncio.get_running_loop()
    client = anthropic.Anthropic()
    initial_message = "You are a natural language interface interpreter for a todo app. User input has been translated through speech to text so interpret the request assuming minor transcription errors.\n\nLists:\n"
    todo_lists = ""
    selected_list = ""
    lists = db.list_lists()
    for i, item in enumerate(lists):
        todo_lists += f"{i + 1}. {item[1]}\n"
    initial_message += todo_lists

    todos = db.select_list(db.selected_list)
    selected_list += f"\nSelected list: {todos.name}\n"
    all_todos = todos.read_all()
    for i, item in enumerate(all_todos):
        selected_list += f"{i + 1}. {item[1]}\n"
    initial_message += selected_list

    history = []

    if initial is not None:
        jsondata = json.dumps(initial)
        yield f"data: {jsondata}\n\n"
        yield 'data: {"finish_reason": "stop"}\n\n'

    jsondata = json.dumps({
        "content": {"title": account['name'], "text": f"""Welcome, {account['name']}.
        
Please save this url somewhere safe and use it to access your todos in the future.

Do not share the url.

Your lists:
{todo_lists}
{selected_list}
"""}})
    print("welcome!", jsondata)
    yield f"data: {jsondata}\n\n"
    yield 'data: {"finish_reason": "stop"}\n\n'

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
                system=initial_message,
                messages=history))

        assistant_content = []
        for x in result.content:
            if x.type == "text":
                assistant_content.append({"type": "text", "text": x.text})
                jsondata = json.dumps({"content": {"text": x.text}})
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
                tool_output = ALL_TOOLS[tool_name]["tool"](db, **tool_input)
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
                            "content": tool_output["text"]
                        }
                    ]
                })
                print("GOT RESULT", result)
                print("TOOL OUTPUT", tool_output)
                jsondata = json.dumps({
                    "content": tool_output
                })
                yield f"data: {jsondata}\n\n"
                yield 'data: {"finish_reason": "stop"}\n\n'
        if len(assistant_content):
            history.append({"role": "assistant", "content": assistant_content})
        print("new history", history)
        yield 'data: {"finish_reason": "stop"}\n\n'


@app.get("/account/{account_id}/conversation")
async def conversation(account_id: str):
    conv_id = str(uuid.uuid4())
    queue = asyncio.Queue()
    db = todostore.Lists(f"db/{account_id}.db")
    # await queue.put({
    #     "role": "user",
    #     "content": "Hello"
    # })
    a = todoaccounts.Accounts()
    account = a.get_account(account_id)
    convs[conv_id] = queue
    return StreamingResponse(
        event_generator(db, queue, account, initial={"id": conv_id}),
        media_type="text/event-stream"
    )


@app.post("/chat/{cid}")
async def chat(cid, text: str = Form(...)):
    await convs[cid].put({"role": "user", "content": text})
    return {}

