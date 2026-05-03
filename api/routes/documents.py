"""/documents endpoints — list, upload, fetch file, delete."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from auth import get_user_id
from config import MAX_PDF_BYTES
from llm import embed_texts
from pdf import chunk_pages, extract_pdf_text
import rag

router = APIRouter()


@router.get("/documents")
async def documents_list(user_id: str = Depends(get_user_id)):
    return await rag.list_documents(user_id)


@router.post("/documents/upload")
async def documents_upload(
    file: UploadFile = File(...),
    user_id: str = Depends(get_user_id),
):
    name = file.filename or "untitled.pdf"
    if not name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported.")
    data = await file.read()
    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large (max {MAX_PDF_BYTES // 1024 // 1024} MB).",
        )

    try:
        pages = extract_pdf_text(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {e}")
    if not pages:
        raise HTTPException(status_code=400, detail="No extractable text in this PDF.")

    chunks = chunk_pages(pages)
    if not chunks:
        raise HTTPException(status_code=400, detail="Could not chunk PDF text.")

    try:
        embeddings = await embed_texts([c["content"] for c in chunks], input_type="passage")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Embedding failed: {e}")
    if len(embeddings) != len(chunks):
        raise HTTPException(status_code=502, detail="Embedding count mismatch.")

    return await rag.store_document(name, pages, chunks, embeddings, data, user_id)


@router.get("/documents/{doc_id}/file")
async def documents_file(doc_id: str, user_id: str = Depends(get_user_id)):
    res = await rag.get_document_file(doc_id, user_id)
    if not res:
        raise HTTPException(status_code=404, detail="document not found")
    pdf_bytes, filename, mime = res
    return Response(
        content=pdf_bytes,
        media_type=mime,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.delete("/documents/{doc_id}")
async def documents_delete(doc_id: str, user_id: str = Depends(get_user_id)):
    await rag.delete_document(doc_id, user_id)
    return {"deleted": doc_id}
