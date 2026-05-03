"""FastAPI entry point for the headless browser microservice.

File map:
  main.py         — FastAPI app + lifespan + routes (this file)
  browser_pool.py — Singleton Playwright Chromium handle
  extract.py      — Render a URL → text + optional screenshot
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

import browser_pool
from extract import render_and_extract


@asynccontextmanager
async def lifespan(app: FastAPI):
    await browser_pool.ensure_browser()
    yield
    await browser_pool.close()


app = FastAPI(title="Browser Service", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "browser_ready": browser_pool.is_ready()}


@app.get("/browse")
async def browse(url: str, max_chars: int = 4000, screenshot: bool = False):
    return await render_and_extract(url, max_chars=max_chars, screenshot=screenshot)
