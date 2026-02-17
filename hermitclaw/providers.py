"""LLM calls via Ollama."""

from __future__ import annotations

import json
import uuid
import requests

from hermitclaw.config import config

OLLAMA_BASE = config.get("ollama_base", "http://localhost:11434")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web for information. Returns titles, snippets, and URLs. "
                "Use this to research topics, find papers, look up facts, or explore "
                "anything you're curious about."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for"},
                    "max_results": {"type": "integer", "description": "Number of results (default 5)", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shell",
            "description": (
                "Run a shell command inside your environment folder. "
                "You can use ls, cat, mkdir, mv, cp, touch, echo, tee, find, grep, head, tail, wc, etc. "
                "You can also run Python scripts: 'python script.py' or 'python -c \"code\"'. "
                "Use 'cat > file.txt << EOF' or 'echo ... > file.txt' to write files. "
                "Create folders with mkdir. Organize however you like. "
                "All paths are relative to your environment root."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to run"}
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "respond",
            "description": (
                "Talk to the person outside! Use this whenever you hear their voice and want to "
                "reply. After you speak, they might say something back — if they do, "
                "use respond AGAIN to keep the conversation going."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "What you say back to them"}
                },
                "required": ["message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "move",
            "description": (
                "Move to a location in your room. Use this to go where feels natural "
                "for what you're doing — desk for writing, bookshelf for research, "
                "window for pondering, bed for resting."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "enum": ["desk", "bookshelf", "window", "plant", "bed", "rug", "center"],
                    }
                },
                "required": ["location"],
            },
        },
    },
]


def chat(messages: list, tools: bool = True, instructions: str = None, max_tokens: int = 300) -> dict:
    """

    Call Ollama chat API. Returns:
    {
        "text": str or None,
        "tool_calls": [{"name": str, "arguments": dict, "call_id": str}],
        "output": list,   # messages to append back to input for tool loops
    }
    """
    # Build messages list with system prompt
    ollama_messages = []
    if instructions:
        ollama_messages.append({"role": "system", "content": instructions})

    for msg in messages:
        if isinstance(msg, dict):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            # Handle multimodal content (images) — flatten to text for now
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, dict):
                        if part.get("type") in ("input_text", "text"):
                            text_parts.append(part["text"])
                    elif isinstance(part, str):
                        text_parts.append(part)
                content = "\n".join(text_parts)
            ollama_messages.append({"role": role, "content": str(content)})

    payload = {
        "model": config["model"],
        "messages": ollama_messages,
        "stream": False,
        "options": {"num_predict": max_tokens},
    }
    if tools:
        payload["tools"] = TOOLS

    resp = requests.post(
        f"{OLLAMA_BASE}/api/chat",
        json=payload,
        timeout=300,
    )
    resp.raise_for_status()
    data = resp.json()

    message = data.get("message", {})
    text = message.get("content") or None
    raw_tool_calls = message.get("tool_calls") or []

    tool_calls = []
    for tc in raw_tool_calls:
        func = tc.get("function", {})
        args = func.get("arguments", {})
        if isinstance(args, str):
            args = json.loads(args)
        tool_calls.append({
            "name": func.get("name", ""),
            "arguments": args,
            "call_id": tc.get("id") or str(uuid.uuid4())[:8],
        })

    # Build output in a format brain.py can append back to input
    output_messages = []
    assistant_msg = {"role": "assistant", "content": text or ""}
    if raw_tool_calls:
        assistant_msg["tool_calls"] = raw_tool_calls
    output_messages.append(assistant_msg)

    return {
        "text": text,
        "tool_calls": tool_calls,
        "output": output_messages,
    }


def embed(text: str) -> list[float]:
    """Get an embedding vector via Ollama."""
    resp = requests.post(
        f"{OLLAMA_BASE}/api/embed",
        json={"model": config.get("embedding_model", "nomic-embed-text"), "input": text},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["embeddings"][0]


def chat_short(messages: list, instructions: str = None) -> str:
    """Short LLM call (importance scoring, reflections) — just text, no tools."""
    result = chat(messages, tools=False, instructions=instructions)
    return result["text"] or ""
