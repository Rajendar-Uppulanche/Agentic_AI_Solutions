# Start Here — Beginner Guide

> If `TODAY_Agent_Project_Crash_Course.md` feels like too much code too fast, read this first.
> Every example here is tiny, runnable on its own, and explained line by line. No production code, no shortcuts — just "what does this piece actually do."

---

## Before anything else: what are we building?

A program that:
1. Gets a question or a problem ("this IP address looks suspicious")
2. Asks an AI what to do about it
3. If the AI needs more info, the program goes and gets it
4. Gives the AI that info, asks again
5. Eventually the AI says "here's my answer" and the program returns it

That's the whole project. Every topic below is just one small piece of making that work reliably. Nothing here is more complicated than that five-step list — it just takes a few new tools to build it properly.

---

## 1. `async` / `await` — "wait without freezing"

**The problem it solves:** normal Python code does one thing, waits for it to finish, then does the next thing. If you're waiting on a network call (like asking an AI a question), your whole program just sits there frozen, doing nothing else.

**Tiny example:**
```python
import asyncio

async def say_hello():          # "async def" = this function can pause and let other things run
    print("Starting...")
    await asyncio.sleep(2)      # "await" = pause here for 2 seconds, but don't freeze everything
    print("Done!")

asyncio.run(say_hello())        # this is how you actually start it running
```
Run this yourself — it prints "Starting...", waits 2 seconds, then prints "Done!". Nothing new yet.

**Where it gets useful — doing two things at once:**
```python
import asyncio

async def task(name, seconds):
    await asyncio.sleep(seconds)
    print(f"{name} finished")

async def main():
    # Without asyncio.gather, these would run one after another: 3 + 2 = 5 seconds total.
    # With gather, they run AT THE SAME TIME: only 3 seconds total (the longest one).
    await asyncio.gather(
        task("A", 3),
        task("B", 2),
    )

asyncio.run(main())
```
**Why your project needs this:** if the AI asks for two lookups (check this IP, check that log), you don't want to do them one at a time. `asyncio.gather` runs them together.

**Rule of thumb:** any function that talks to the internet (calling the AI, calling an API) should be `async def`. Plain calculations don't need to be.

---

## 2. Pydantic — "a strict form that rejects bad data"

**The problem it solves:** normal Python dictionaries don't check anything. `{"severty": "hihg"}` (typos and all) is just as valid as a correct one. That's dangerous when an AI is filling in the data.

**Tiny example:**
```python
from pydantic import BaseModel

class Person(BaseModel):
    name: str
    age: int

# This works — "30" gets auto-converted to the int 30
p = Person(name="Alex", age="30")
print(p.age)          # 30 (as a real integer, not text)

# This fails loudly — "thirty" can't become a number
p2 = Person(name="Alex", age="thirty")   # raises an error immediately
```
**Why your project needs this:** you use it in two places —
1. To check incoming requests are shaped correctly ("this must have an `alert` field, and it must be text").
2. To force the AI's final answer into a fixed shape ("severity must be exactly `low`, `medium`, `high`, or `critical` — nothing else allowed").

---

## 3. REST APIs — you probably already know this

GET = read something, POST = create/do something, and status codes like `200` (all good) or `400` (you sent something wrong). If you've built any web backend before, skip ahead — nothing here is new for the project, just applied to AI instead of a database.

---

## 4. FastAPI — "the doorway into your program"

**The problem it solves:** your agent logic is just Python functions. Something needs to let *other computers* call those functions over the internet. That's what a web framework does.

**The smallest possible FastAPI app:**
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/hello")              # when someone visits /hello...
async def hello():
    return {"message": "hi"}    # ...they get this back as JSON
```
Run it with `uvicorn filename:app --reload`, then visit `http://127.0.0.1:8000/hello` in a browser — you'll see `{"message": "hi"}`.

That's it. Your real project just has more routes (`/triage` instead of `/hello`) and those routes do more work before replying.

---

## 5. Calling the LLM — "how your code actually talks to the AI"

**Tiny example:**
```python
from openai import OpenAI

client = OpenAI(api_key="sk-...")     # your key, from .env in the real project

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "Say hello in one word."}
    ],
)

print(response.choices[0].message.content)   # the AI's reply, as plain text
```
**What's happening:** `messages` is a list — like a chat transcript. You send the whole conversation so far, the AI adds its reply. Your project's agent loop just keeps *adding to this list* every time a tool runs, and sends the whole thing again.

---

## 6. JSON & structured output — "make the AI fill in a form, not write an essay"

**The problem:** by default, the AI replies with sentences. Your code can't reliably pull data out of a sentence. You need it to reply in a fixed, predictable shape.

**Tiny example, combining Pydantic + the AI call:**
```python
from pydantic import BaseModel
from openai import OpenAI

class Answer(BaseModel):
    mood: str
    confidence: float

client = OpenAI(api_key="sk-...")

response = client.chat.completions.parse(          # note: .parse, not .create
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "I just got promoted!"}],
    response_format=Answer,                          # ← forces the reply into this shape
)

result = response.choices[0].message.parsed
print(result.mood, result.confidence)                 # already a real Python object, not text to parse yourself
```
This is the exact same trick your real project uses for the final `SecurityVerdict` — just a smaller example.

---

## 7. LangChain / LangGraph — "a shortcut so you don't hand-write the loop"

You don't need to learn this deeply for an "overview." The one thing to understand:

```python
from langchain_core.tools import tool
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

@tool
def get_weather(city: str) -> str:
    """Look up the weather for a city."""     # ← the AI reads this description to know when to use it
    return f"{city}: sunny, 75°F"

llm = ChatOpenAI(model="gpt-4o-mini", api_key="sk-...")
agent = create_agent(llm, tools=[get_weather])

result = agent.invoke({"messages": [("user", "What's the weather in Austin?")]})
print(result["messages"][-1].content)
```
Compare this to Topic 5 + 6 combined — LangChain is doing the same "ask AI → maybe call a tool → ask again" loop internally, so you don't write the `while` loop yourself. That's the entire value proposition.

---

## 8. Putting it all together — a tiny version of the real agent

This is the whole project, shrunk down to ~20 lines, with nothing hidden:

```python
import asyncio
import json
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key="sk-...")

async def get_weather(city: str) -> str:          # a "tool" — just a normal async function
    return f"{city}: sunny, 75°F (pretend data)"

tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the weather for a city",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    },
}]

async def run_agent(question: str) -> str:
    messages = [{"role": "user", "content": question}]

    resp = await client.chat.completions.create(model="gpt-4o-mini", messages=messages, tools=tools)
    msg = resp.choices[0].message
    messages.append(msg)

    if msg.tool_calls:                                       # the AI wants to use a tool
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments)          # arguments arrive as JSON text
            result = await get_weather(**args)                    # actually run the tool
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

        resp = await client.chat.completions.create(model="gpt-4o-mini", messages=messages)  # ask again with the result

    return resp.choices[0].message.content

print(asyncio.run(run_agent("What's the weather in Austin?")))
```

**Read this line by line until it makes sense.** Your real `agents/triage_agent.py` is this exact same shape — it just has a `while`/`for` loop around the "ask again" part (so it can call tools more than once), runs multiple tools with `asyncio.gather` instead of one at a time, and forces the final answer through Pydantic (`Answer` from Topic 6) instead of returning plain text.

---

## Where to go next

Once each piece above makes sense on its own:
1. Open `agents/triage_agent.py` in the real project — it should now look like "the tiny example, but more careful" instead of "a wall of unfamiliar code."
2. Then read `How_This_Project_Works.md` for the full real walkthrough.
3. `TODAY_Agent_Project_Crash_Course.md` is the deep reference — come back to it once the basics feel solid, to see the production-grade version of each idea (retries, timeouts, error handling).

You don't need to memorize any of this. The goal is just: when you see `await`, `BaseModel`, `@app.post`, or `tool_calls` in the real code, you have a small mental picture of what it's doing, instead of it being a wall of unfamiliar symbols.
