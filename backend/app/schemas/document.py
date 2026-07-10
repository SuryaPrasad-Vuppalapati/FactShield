"""Pydantic schemas for Document upload and management."""

from __future__ import annotations

import datetime
import uuid

from pydantic import BaseModel, Field


class DocumentUploadRequest(BaseModel):
    """Request schema for uploading/indexing a document."""

    filename: str = Field(..., description="The name of the file.")
    content: str = Field(..., description="The plain text content of the document.")
    owner_role: str = Field(
        "student", description="The role of the owner ('student' or 'teacher')."
    )


class DocumentUploadResponse(BaseModel):
    """Response schema for a successful document upload."""

    doc_id: uuid.UUID = Field(
        ..., description="The unique database identifier for the indexed document."
    )
    filename: str = Field(..., description="The name of the file.")
    chunk_count: int = Field(
        ..., description="The number of parsed and embedded text chunks."
    )


class DocumentItem(BaseModel):
    """Details of a single indexed document."""

    id: uuid.UUID = Field(..., description="The unique document identifier.")
    filename: str = Field(..., description="The name of the file.")
    owner_role: str = Field(..., description="Role of the owner.")
    uploaded_at: datetime.datetime = Field(
        ..., description="Timestamp when the file was uploaded."
    )


class DocumentListResponse(BaseModel):
    """Response containing list of uploaded documents."""

    documents: list[DocumentItem] = Field(..., description="The list of documents.")
