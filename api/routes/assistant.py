"""Assistant panel endpoint — autonomous goal-driven crawl with live SSE.

POST /assistant/run  body: {start_url, goal, max_pages?, same_domain?}
Streams events to the right-side Assistant panel in the web client.
"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from agents.crawler import run_crawler
from auth import get_user_id

router = APIRouter()


class CrawlRequest(BaseModel):
    start_url: str
    goal: str
    max_pages: Optional[int] = None
    max_actions_per_page: Optional[int] = None
    same_domain: bool = True


@router.post("/assistant/run")
async def assistant_run(req: CrawlRequest, user_id: str = Depends(get_user_id)):
    async def event_stream():
        async for evt in run_crawler(
            start_url=req.start_url.strip(),
            goal=req.goal.strip(),
            max_pages=req.max_pages or 8,
            max_actions_per_page=req.max_actions_per_page or 4,
            same_domain=req.same_domain,
        ):
            yield evt

    return EventSourceResponse(event_stream())
