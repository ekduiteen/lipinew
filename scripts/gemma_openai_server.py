from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from typing import Any

import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoProcessor


MODEL_PATH = os.getenv("MODEL_PATH", "/data/models/llm/gemma-4-E4B-it")
MODEL_NAME = os.getenv("MODEL_NAME", "gemma-4-E4B-it")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8100"))
DTYPE = os.getenv("DTYPE", "bfloat16")
MAX_NEW_TOKENS = int(os.getenv("MAX_NEW_TOKENS", "256"))

app = FastAPI(title="Gemma OpenAI Shim")
_lock = asyncio.Lock()

processor: AutoProcessor | None = None
model: AutoModelForCausalLM | None = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[dict[str, Any]]
    stream: bool = False
    max_tokens: int | None = None
    temperature: float | None = None


def _dtype() -> torch.dtype:
    if DTYPE == "float16":
        return torch.float16
    if DTYPE == "float32":
        return torch.float32
    return torch.bfloat16


def _normalize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for message in messages:
        role = str(message.get("role", "user"))
        content = message.get("content", "")

        if isinstance(content, str):
            items = [{"type": "text", "text": content}]
        elif isinstance(content, list):
            items = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    items.append({"type": "text", "text": str(item.get("text", ""))})
        else:
            items = [{"type": "text", "text": str(content)}]

        normalized.append({"role": role, "content": items})
    return normalized


def _generate_text(messages: list[dict[str, Any]], max_tokens: int | None) -> str:
    if processor is None or model is None:
        raise RuntimeError("Model not loaded")

    inputs = processor.apply_chat_template(
        _normalize_messages(messages),
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    )
    inputs = {k: v.to(model.device) for k, v in inputs.items()}

    output = model.generate(
        **inputs,
        max_new_tokens=max_tokens or MAX_NEW_TOKENS,
        do_sample=False,
    )
    text = processor.batch_decode(
        output[:, inputs["input_ids"].shape[1]:],
        skip_special_tokens=True,
    )[0]
    return text.strip()


@app.on_event("startup")
async def startup_event() -> None:
    global processor, model
    processor = AutoProcessor.from_pretrained(MODEL_PATH, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        dtype=_dtype(),
        device_map="cuda",
        trust_remote_code=True,
    )


@app.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok" if model is not None else "loading",
        "model": MODEL_NAME,
        "device": "cuda",
    }


@app.get("/v1/models")
async def list_models() -> dict[str, Any]:
    return {
        "object": "list",
        "data": [
            {
                "id": MODEL_NAME,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "gemma-shim",
            }
        ],
    }


@app.post("/v1/chat/completions", response_model=None)
async def chat_completions(req: ChatCompletionRequest):
    if req.model != MODEL_NAME:
        raise HTTPException(status_code=404, detail=f"Model {req.model!r} not available")

    async with _lock:
        text = await asyncio.to_thread(_generate_text, req.messages, req.max_tokens)

    created = int(time.time())
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"

    if req.stream:
        async def event_stream():
            chunk = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": MODEL_NAME,
                "choices": [
                    {"index": 0, "delta": {"content": text}, "finish_reason": None}
                ],
            }
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            done = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": MODEL_NAME,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            }
            yield f"data: {json.dumps(done, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    payload = {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": MODEL_NAME,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }
    return JSONResponse(payload)


if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT)
