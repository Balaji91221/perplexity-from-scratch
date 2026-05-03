"""GET / DELETE /threads endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from auth import get_user_id
import threads_repo

router = APIRouter()


@router.get("/threads")
async def list_threads(user_id: str = Depends(get_user_id)):
    return await threads_repo.list_threads(user_id)


@router.get("/threads/{thread_id}")
async def get_thread(thread_id: str, user_id: str = Depends(get_user_id)):
    t = await threads_repo.get_thread_with_messages(thread_id, user_id)
    if not t:
        raise HTTPException(status_code=404, detail="thread not found")
    return t


@router.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str, user_id: str = Depends(get_user_id)):
    await threads_repo.delete_thread(thread_id, user_id)
    return {"deleted": thread_id}
