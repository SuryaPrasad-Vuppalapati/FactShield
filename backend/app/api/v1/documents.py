"""FastAPI router for document uploads and management under /api/v1/documents."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from sqlalchemy import select

from app.db.session import async_session_maker
from app.models.chunk import Chunk
from app.models.document import Document
from app.retrieval.chunking import chunk_document
from app.retrieval.embeddings import embed_batch
from app.retrieval.parsing import extract_text_from_file
from app.schemas.document import (
    DocumentItem,
    DocumentListResponse,
    DocumentUploadResponse,
)

router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),  # noqa: B008
    owner_role: str = Form("student"),  # noqa: B008
) -> DocumentUploadResponse:
    """Upload, parse, chunk, embed, and index a document in the vector database."""
    if owner_role not in ("student", "teacher"):
        raise HTTPException(
            status_code=400,
            detail="owner_role must be either 'student' or 'teacher'.",
        )

    # 1. Read file bytes and parse to plain text
    try:
        file_bytes = await file.read()
        filename = file.filename or "uploaded_document.txt"
        
        chunks = []
        if filename.lower().endswith(".pdf"):
            import pypdf
            from io import BytesIO
            reader = pypdf.PdfReader(BytesIO(file_bytes))
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    # Fix: Strip null bytes from PDF text to prevent Postgres encoding errors
                    page_text = page_text.replace("\x00", "")
                    page_chunks = chunk_document(page_text)
                    for pc in page_chunks:
                        chunks.append(f"[Page {i+1}] {pc}")
        else:
            content = extract_text_from_file(file_bytes, filename)
            content = content.replace("\x00", "")
            chunks = chunk_document(content)
            
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to read or parse file: {str(e)}",
        ) from e

    # 2. Split text into chunks
    if not chunks:
        raise HTTPException(
            status_code=400,
            detail="Document text contains no indexable content.",
        )

    # 3. Compute embeddings in batch
    embeddings = embed_batch(chunks)

    # 4. Save to database
    db_doc = Document(
        owner_role=owner_role,
        filename=filename,
    )

    async with async_session_maker() as session:
        session.add(db_doc)
        await session.flush()
        doc_id = db_doc.id

        # Insert chunks
        for idx, (content_chunk, embedding) in enumerate(
            zip(chunks, embeddings, strict=True)
        ):
            db_chunk = Chunk(
                document_id=doc_id,
                content=content_chunk,
                chunk_index=idx,
                embedding=embedding,
            )
            session.add(db_chunk)

        await session.commit()

    return DocumentUploadResponse(
        doc_id=doc_id,
        filename=filename,
        chunk_count=len(chunks),
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents() -> DocumentListResponse:
    """Retrieve a list of all uploaded and indexed documents."""
    async with async_session_maker() as session:
        stmt = select(Document).order_by(Document.uploaded_at.desc())
        result = await session.execute(stmt)
        docs = result.scalars().all()
        return DocumentListResponse(
            documents=[
                DocumentItem(
                    id=doc.id,
                    filename=doc.filename,
                    owner_role=doc.owner_role,
                    uploaded_at=doc.uploaded_at,
                )
                for doc in docs
            ]
        )


@router.get("/{doc_id}", response_model=DocumentItem)
async def get_document(doc_id: str) -> DocumentItem:
    """Retrieve one document's metadata for clickable citation links."""
    import uuid

    try:
        parsed_id = uuid.UUID(doc_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid UUID format.") from e

    async with async_session_maker() as session:
        stmt = select(Document).where(Document.id == parsed_id)
        result = await session.execute(stmt)
        doc = result.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found.")

        return DocumentItem(
            id=doc.id,
            filename=doc.filename,
            owner_role=doc.owner_role,
            uploaded_at=doc.uploaded_at,
        )


@router.delete("/{doc_id}")
async def delete_document(doc_id: str) -> dict[str, str]:
    """Delete a document and its chunks from the database/vector store."""
    import uuid
    try:
        parsed_id = uuid.UUID(doc_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid UUID format.") from e

    async with async_session_maker() as session:
        # Find document
        stmt = select(Document).where(Document.id == parsed_id)
        result = await session.execute(stmt)
        doc = result.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found.")

        await session.delete(doc)
        await session.commit()

    return {"status": "success", "message": f"Document {doc_id} deleted."}


@router.post("/extract-text")
async def extract_text(
    file: UploadFile = File(...),  # noqa: B008
) -> dict[str, str]:
    """Extract text from an uploaded document without saving or indexing it."""
    try:
        file_bytes = await file.read()
        filename = file.filename or "uploaded_student_answer.txt"
        text = extract_text_from_file(file_bytes, filename)
        return {"text": text, "filename": filename}
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse student answer file: {str(e)}",
        ) from e
