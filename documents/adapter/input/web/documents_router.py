from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from documents.adapter.input.web.request.register_document_request import RegisterDocumentRequest
from documents.adapter.input.web.request.search_document_request import DocumentSearchRequest
from documents.adapter.input.web.response.search_document_response import DocumentSearchResponse, DocumentItemResponse
from documents.application.usecase.document_usecase import DocumentUseCase

documents_router = APIRouter(tags=["documents"])

document_usecase = DocumentUseCase.getInstance()

from account.adapter.input.web.session_helper import get_current_user

@documents_router.post("/register")
async def register_document(payload: RegisterDocumentRequest, user_id: int = Depends(get_current_user)):
    doc = document_usecase.register_document(payload.file_name, payload.s3_key, user_id)
    return {
        "id": doc.id,
        "file_name": doc.file_name,
        "s3_key": doc.s3_key,
        "uploader_id": doc.uploader_id,
    }

@documents_router.get("/list")
async def list_documents():
    return document_usecase.list_documents()

@documents_router.post("/search", response_model=DocumentSearchResponse)
async def search_documents(payload: DocumentSearchRequest):
    docs = document_usecase.search_documents(
        file_name=payload.file_name,
        uploaded_from=payload.uploaded_from,
        uploaded_to=payload.uploaded_to,
        updated_from=payload.updated_from,
        updated_to=payload.updated_to,
        page=payload.page,
        size=payload.size
    )

    if not docs:
        return DocumentSearchResponse(
            total=0,
            page=payload.page,
            size=payload.size,
            data=[],
            message="검색 결과 없음"
        )

    data = [
        DocumentItemResponse(
            id=d.id,
            file_name=d.file_name,
            uploader_id=d.uploader_id,
            uploaded_at=d.uploaded_at,
            updated_at=d.updated_at
        )
        for d in docs
    ]

    return DocumentSearchResponse(
        total=len(data),
        page=payload.page,
        size=payload.size,
        data=data
    )