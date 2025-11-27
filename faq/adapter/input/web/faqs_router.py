from fastapi import APIRouter, HTTPException, status, Depends # 🌟 Depends 임포트
from typing import List

from faq.adapter.input.web.response.list_faq_response import FAQListResponse
from faq.application.usecase.faq_usecase import FAQUseCase
from faq.domain.faq import FAQItem

# DTO 임포트 (동일)
from faq.adapter.input.web.request.register_faq_request import RegisterFAQRequest
from faq.adapter.input.web.request.search_faq_request import SearchFAQRequest
from faq.adapter.input.web.response.register_faq_response import RegisterFAQResponse
from faq.adapter.input.web.response.search_faq_response import SearchFAQResponse, FAQSummary

usecase = FAQUseCase().get_instance()
faqs_router = APIRouter(tags=["faqs"])


# --- 1. 등록 엔드포인트: POST /register (동일) ---
@faqs_router.post("/register", response_model=RegisterFAQResponse, status_code=status.HTTP_201_CREATED)
async def register_faq(
        payload: RegisterFAQRequest
):
    """
    새로운 FAQ 항목을 등록합니다.
    """
    try:
        # 1. UseCase 호출 (전역 변수 'usecase' 사용)
        faq_item: FAQItem = usecase.register_faq(
            question=payload.question,
            answer=payload.answer,
            category=payload.category
        )

        # 2. Domain Object -> Response DTO 맵핑 및 반환 (동일)
        return RegisterFAQResponse(
            id=faq_item.id,
            question=faq_item.question,
            category=faq_item.category,
            created_at=faq_item.created_at
        )

    except ValueError as e:
        # 도메인 유효성 검사 오류 (예: 질문 공백)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"FAQ 등록 중 서버 오류 발생: {e}")


# --- 2. 목록 조회 엔드포인트: GET /list (동일) ---
@faqs_router.get("/list", response_model=FAQListResponse)
async def list_faqs(
        # 🚨 DI 매개변수 제거 (전역 usecase 사용 요청에 따름)
):
    try:
        # UseCase 호출 (전역 변수 'usecase' 사용)
        faq_items: List[FAQItem] = usecase.list_faqs()

        summary_items: List[FAQSummary] = [
            FAQSummary(
                id=d.id,
                question=d.question,
                answer_preview=d.answer[:100] + ("..." if len(d.answer) > 100 else ""),
                category=d.category,
                view_count=d.view_count,
                created_at=d.created_at
            )
            for d in faq_items
        ]
        return FAQListResponse(items=summary_items)

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"FAQ 목록 조회 중 서버 오류 발생: {e}")


# --- 3. 검색 엔드포인트: GET/POST /search (수정됨: 무한 스크롤 적용) ---
@faqs_router.post("/search", response_model=SearchFAQResponse)
async def search_faqs(
        payload: SearchFAQRequest,
        # 🚨 DI 매개변수 제거 (전역 usecase 사용 요청에 따름)
):
    """
    검색 조건과 무한 스크롤 방식에 따라 FAQ 목록을 조회합니다.
    """
    # 1. UseCase 호출 (UseCase는 이제 (항목 리스트, has_next) 튜플을 반환)
    faq_items: List[FAQItem]
    has_next: bool

    faq_items, has_next = usecase.search_faqs(
        category=payload.category,
        query=payload.query,
        created_from=payload.created_from,
        created_to=payload.created_to,
        updated_from=payload.updated_from,
        updated_to=payload.updated_to,
        page=payload.page,
        size=payload.size
    )

    # 2. 검색 결과 없음 처리 (total_count 필드가 제거되었으므로 응답 구조 변경)
    if not faq_items:
        return SearchFAQResponse(
            items=[],
            has_next=False,
            message="검색 결과 없음"
        )

    # 3. Domain Object 목록 -> Response DTO 목록(FAQSummary) 맵핑 (조회수 포함)
    summary_data = [
        FAQSummary(
            id=d.id,
            question=d.question,
            # 답변 미리보기 처리 (100자 제한)
            answer_preview=d.answer[:100] + ("..." if len(d.answer) > 100 else ""),
            category=d.category,
            view_count=d.view_count,  # 👈 조회수
            created_at=d.created_at
        )
        for d in faq_items
    ]

    # 4. 최종 응답 반환 (total_count, page, size 대신 has_next 사용)
    return SearchFAQResponse(
        items=summary_data,
        has_next=has_next,  # 👈 UseCase에서 반환된 값
        message=None
    )


# --- 4. 상세 조회 엔드포인트: GET /detail/{faq_id} ---
# 💡 NotFoundError 처리를 위해 필요한 임포트를 가정합니다.
# from faq.application.exception.faq_exception import NotFoundError

@faqs_router.get("/detail/{faq_id}", response_model=FAQSummary)
async def get_faq_detail(
        faq_id: int  # URL 경로에서 ID를 받습니다.
):
    """
    특정 FAQ 항목의 상세 내용을 조회하고, 조회수를 1 증가시킵니다.
    """
    try:
        # 1. UseCase 호출: 상세 정보를 가져오고 조회수를 증가시킵니다.
        #    FAQItem 도메인 객체를 반환한다고 가정합니다.
        faq_item: FAQItem = usecase.get_faq_detail(faq_id=faq_id)

        # 2. Domain Object -> Response DTO 맵핑 및 반환
        return FAQSummary(
            id=faq_item.id,
            question=faq_item.question,
            # 💡 상세 조회 응답은 전체 답변을 포함해야 합니다.
            answer_preview=faq_item.answer,
            category=faq_item.category,
            view_count=faq_item.view_count,  # 💡 증가된 조회수
            created_at=faq_item.created_at
        )

    # 💡 도메인/유스케이스 레이어에서 해당 FAQ가 없을 경우 발생하는 예외
    except Exception as e:
        # 이전에 발생했던 404 오류를 처리하기 위해, 특정 예외를 404로 변환해야 합니다.
        if "not found" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"FAQ ID {faq_id}를 찾을 수 없습니다.")
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"FAQ 상세 조회 중 서버 오류 발생: {e}")