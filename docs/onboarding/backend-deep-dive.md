# 🔧 백엔드 상세 가이드

> FastAPI + 헥사고날 아키텍처 심층 분석

## 📋 목차

1. [새 기능 추가하기](#새-기능-추가하기)
2. [라우터 작성법](#라우터-작성법)
3. [UseCase 패턴](#usecase-패턴)
4. [LLM 프로바이더 시스템](#llm-프로바이더-시스템)
5. [세션 관리](#세션-관리)
6. [에러 처리](#에러-처리)

---

## 새 기능 추가하기

새로운 기능(바운디드 컨텍스트)을 추가할 때 따라야 할 단계입니다.

### 예시: "알림(notification)" 기능 추가

#### Step 1: 도메인 엔티티 정의

```python
# notification/domain/notification.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum

class NotificationType(Enum):
    ANALYSIS_COMPLETE = "analysis_complete"
    SYSTEM_ALERT = "system_alert"

@dataclass
class Notification:
    """알림 도메인 엔티티 - 순수 Python, 외부 의존성 없음"""
    id: Optional[int] = None
    user_id: int = 0
    notification_type: NotificationType = NotificationType.SYSTEM_ALERT
    title: str = ""
    message: str = ""
    is_read: bool = False
    created_at: Optional[datetime] = None
    
    def mark_as_read(self):
        """읽음 처리 - 비즈니스 로직"""
        self.is_read = True
```

#### Step 2: Port 인터페이스 정의

```python
# notification/application/port/notification_repository_port.py
from abc import ABC, abstractmethod
from typing import List, Optional
from notification.domain.notification import Notification

class NotificationRepositoryPort(ABC):
    """알림 저장소 인터페이스 - UseCase가 의존하는 추상화"""
    
    @abstractmethod
    def save(self, notification: Notification) -> Notification:
        """알림 저장"""
        pass
    
    @abstractmethod
    def find_by_id(self, notification_id: int) -> Optional[Notification]:
        """ID로 알림 조회"""
        pass
    
    @abstractmethod
    def find_by_user_id(self, user_id: int, unread_only: bool = False) -> List[Notification]:
        """사용자의 알림 목록 조회"""
        pass
    
    @abstractmethod
    def mark_all_as_read(self, user_id: int) -> int:
        """사용자의 모든 알림 읽음 처리, 처리된 개수 반환"""
        pass
```

#### Step 3: UseCase 구현

```python
# notification/application/usecase/notification_usecase.py
from typing import List, Optional
from notification.domain.notification import Notification, NotificationType
from notification.application.port.notification_repository_port import NotificationRepositoryPort

class NotificationUseCase:
    """알림 비즈니스 로직 - Port에만 의존"""
    
    def __init__(self, repository: NotificationRepositoryPort):
        # 구현체가 아닌 인터페이스에 의존
        self.repository = repository
    
    def get_user_notifications(
        self, 
        user_id: int, 
        unread_only: bool = False
    ) -> List[Notification]:
        """사용자 알림 목록 조회"""
        return self.repository.find_by_user_id(user_id, unread_only)
    
    def create_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str
    ) -> Notification:
        """새 알림 생성"""
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message
        )
        return self.repository.save(notification)
    
    def mark_as_read(self, notification_id: int, user_id: int) -> Optional[Notification]:
        """알림 읽음 처리"""
        notification = self.repository.find_by_id(notification_id)
        
        if not notification:
            return None
        
        # 권한 검증 - 본인의 알림만 처리 가능
        if notification.user_id != user_id:
            raise PermissionError("다른 사용자의 알림입니다")
        
        notification.mark_as_read()
        return self.repository.save(notification)
```

#### Step 4: ORM 모델 구현

```python
# notification/infrastructure/orm/notification_orm.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from config.database.session import Base
from notification.domain.notification import Notification, NotificationType

class NotificationORM(Base):
    """SQLAlchemy ORM 모델"""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    notification_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(String(1000), nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    
    @classmethod
    def from_domain(cls, notification: Notification) -> "NotificationORM":
        """도메인 엔티티 → ORM 변환"""
        return cls(
            id=notification.id,
            user_id=notification.user_id,
            notification_type=notification.notification_type.value,
            title=notification.title,
            message=notification.message,
            is_read=notification.is_read,
            created_at=notification.created_at
        )
    
    def to_domain(self) -> Notification:
        """ORM → 도메인 엔티티 변환"""
        return Notification(
            id=self.id,
            user_id=self.user_id,
            notification_type=NotificationType(self.notification_type),
            title=self.title,
            message=self.message,
            is_read=self.is_read,
            created_at=self.created_at
        )
```

#### Step 5: Repository 구현체

```python
# notification/infrastructure/repository/notification_repository_impl.py
from typing import List, Optional
from sqlalchemy.orm import Session
from notification.application.port.notification_repository_port import NotificationRepositoryPort
from notification.domain.notification import Notification
from notification.infrastructure.orm.notification_orm import NotificationORM

class NotificationRepositoryImpl(NotificationRepositoryPort):
    """Port의 실제 구현 - MySQL 사용"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def save(self, notification: Notification) -> Notification:
        orm_model = NotificationORM.from_domain(notification)
        
        if orm_model.id:
            # 업데이트
            self.db.merge(orm_model)
        else:
            # 새로 생성
            self.db.add(orm_model)
        
        self.db.commit()
        self.db.refresh(orm_model)
        return orm_model.to_domain()
    
    def find_by_id(self, notification_id: int) -> Optional[Notification]:
        orm_model = self.db.query(NotificationORM).filter(
            NotificationORM.id == notification_id
        ).first()
        return orm_model.to_domain() if orm_model else None
    
    def find_by_user_id(self, user_id: int, unread_only: bool = False) -> List[Notification]:
        query = self.db.query(NotificationORM).filter(
            NotificationORM.user_id == user_id
        )
        
        if unread_only:
            query = query.filter(NotificationORM.is_read == False)
        
        orm_models = query.order_by(NotificationORM.created_at.desc()).all()
        return [orm.to_domain() for orm in orm_models]
    
    def mark_all_as_read(self, user_id: int) -> int:
        result = self.db.query(NotificationORM).filter(
            NotificationORM.user_id == user_id,
            NotificationORM.is_read == False
        ).update({"is_read": True})
        
        self.db.commit()
        return result
```

#### Step 6: 라우터 구현

```python
# notification/adapter/input/web/notification_router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from config.database.session import get_db
from account.adapter.input.web.session_helper import get_current_user
from notification.application.usecase.notification_usecase import NotificationUseCase
from notification.infrastructure.repository.notification_repository_impl import NotificationRepositoryImpl

router = APIRouter(tags=["Notification"])

# === 의존성 주입 (모듈 레벨에서 정의) ===
def get_notification_usecase(db: Session = Depends(get_db)) -> NotificationUseCase:
    repository = NotificationRepositoryImpl(db)
    return NotificationUseCase(repository)


# === Response DTO ===
class NotificationResponse(BaseModel):
    id: int
    notification_type: str
    title: str
    message: str
    is_read: bool
    created_at: str

    class Config:
        from_attributes = True


# === API 엔드포인트 ===
@router.get("/list", response_model=List[NotificationResponse])
async def get_notifications(
    unread_only: bool = False,
    user_id: str = Depends(get_current_user),  # 세션에서 사용자 ID 추출
    usecase: NotificationUseCase = Depends(get_notification_usecase)
):
    """사용자의 알림 목록 조회"""
    notifications = usecase.get_user_notifications(int(user_id), unread_only)
    return [
        NotificationResponse(
            id=n.id,
            notification_type=n.notification_type.value,
            title=n.title,
            message=n.message,
            is_read=n.is_read,
            created_at=n.created_at.isoformat() if n.created_at else ""
        )
        for n in notifications
    ]


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    user_id: str = Depends(get_current_user),
    usecase: NotificationUseCase = Depends(get_notification_usecase)
):
    """알림 읽음 처리"""
    try:
        notification = usecase.mark_as_read(notification_id, int(user_id))
        if not notification:
            raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다")
        return {"status": "success"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
```

#### Step 7: main.py에 라우터 등록

```python
# app/main.py
from notification.adapter.input.web.notification_router import router as notification_router

# ... 기존 코드 ...

app.include_router(notification_router, prefix="/notifications")
```

---

## 라우터 작성법

### 의존성 주입 패턴

FastAPI의 `Depends`를 활용한 의존성 주입 패턴입니다:

```python
# 패턴 1: 함수형 의존성
def get_usecase(db: Session = Depends(get_db)) -> MyUseCase:
    repository = MyRepositoryImpl(db)
    return MyUseCase(repository)

@router.get("/items")
async def get_items(usecase: MyUseCase = Depends(get_usecase)):
    return usecase.get_all_items()


# 패턴 2: 클래스형 의존성 (더 복잡한 경우)
class UseCaseDeps:
    def __init__(self, db: Session = Depends(get_db)):
        self.repository = MyRepositoryImpl(db)
        self.external_service = ExternalService()
    
    def get_usecase(self) -> MyUseCase:
        return MyUseCase(self.repository, self.external_service)

deps = UseCaseDeps()

@router.get("/items")
async def get_items(usecase: MyUseCase = Depends(deps.get_usecase)):
    return usecase.get_all_items()
```

### 인증된 요청 처리

```python
from account.adapter.input.web.session_helper import get_current_user

@router.get("/my-data")
async def get_my_data(
    user_id: str = Depends(get_current_user)  # 세션에서 user_id 추출
):
    """로그인 필수 엔드포인트"""
    # user_id가 없으면 자동으로 401 에러 발생
    return {"user_id": user_id}
```

### Request/Response DTO

```python
from pydantic import BaseModel, Field
from typing import Optional

# Request DTO
class CreateItemRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: float = Field(..., gt=0)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "상품명",
                "description": "상품 설명",
                "price": 10000.0
            }
        }

# Response DTO
class ItemResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: float
    created_at: str

    class Config:
        from_attributes = True  # ORM 모델에서 자동 변환 허용
```

---

## UseCase 패턴

### 기본 구조

```python
class MyUseCase:
    """UseCase는 비즈니스 로직의 진입점"""
    
    def __init__(
        self,
        repository: MyRepositoryPort,      # Port (인터페이스)
        external_service: ExternalServicePort  # Port (인터페이스)
    ):
        # 생성자에서 의존성 주입 (인터페이스만!)
        self.repository = repository
        self.external_service = external_service
    
    def execute(self, input_data: InputDTO) -> OutputDTO:
        """비즈니스 로직 실행"""
        # 1. 입력 검증
        self._validate_input(input_data)
        
        # 2. 도메인 로직 실행
        entity = self._process(input_data)
        
        # 3. 저장
        saved_entity = self.repository.save(entity)
        
        # 4. 결과 반환
        return OutputDTO.from_entity(saved_entity)
    
    def _validate_input(self, input_data):
        """입력 검증 로직"""
        pass
    
    def _process(self, input_data):
        """핵심 비즈니스 로직"""
        pass
```

### 비동기 UseCase

```python
import asyncio

class AsyncUseCase:
    """비동기 작업이 필요한 UseCase"""
    
    async def execute(self, input_data):
        # 병렬 실행 (성능 최적화)
        result1, result2 = await asyncio.gather(
            self._async_task1(input_data),
            self._async_task2(input_data)
        )
        return self._combine_results(result1, result2)
```

---

## LLM 프로바이더 시스템

### 프로바이더 팩토리 패턴

```python
# financial_statement/infrastructure/service/llm_providers/provider_factory.py

class LLMProviderFactory:
    """LLM 프로바이더 생성 팩토리"""
    
    @staticmethod
    def create_provider(provider_name: str = None) -> BaseLLMProvider:
        """환경 설정에 따라 적절한 프로바이더 생성"""
        
        provider_name = provider_name or os.getenv("LLM_PROVIDER", "auto")
        
        if provider_name == "openai":
            return OpenAIProvider()
        elif provider_name == "anthropic":
            return AnthropicProvider()
        elif provider_name == "template":
            return TemplateProvider()
        elif provider_name == "auto":
            # 자동 선택: 사용 가능한 첫 번째 프로바이더
            if os.getenv("OPENAI_API_KEY"):
                return OpenAIProvider()
            elif os.getenv("ANTHROPIC_API_KEY"):
                return AnthropicProvider()
            else:
                return TemplateProvider()  # 폴백
        else:
            raise ValueError(f"Unknown provider: {provider_name}")
```

### 새 LLM 프로바이더 추가하기

```python
# 1. BaseLLMProvider 상속
from .base_provider import BaseLLMProvider

class NewLLMProvider(BaseLLMProvider):
    """새로운 LLM 프로바이더"""
    
    def __init__(self):
        self.api_key = os.getenv("NEW_LLM_API_KEY")
        self.model = os.getenv("NEW_LLM_MODEL", "default-model")
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def get_provider_name(self) -> str:
        return "new-llm"
    
    async def generate_text(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.3
    ) -> str:
        """텍스트 생성"""
        # API 호출 구현
        pass
    
    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.3
    ) -> dict:
        """JSON 형식 생성"""
        # API 호출 후 JSON 파싱
        pass

# 2. provider_factory.py에 추가
elif provider_name == "new-llm":
    return NewLLMProvider()
```

---

## 세션 관리

### Redis 세션 구조

```python
# social_oauth/infrastructure/service/redis_session_service.py

import redis
import json
from typing import Optional

class RedisSessionService:
    """Redis 기반 세션 관리"""
    
    def __init__(self):
        self.redis = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True
        )
        self.session_ttl = 86400  # 24시간
    
    def create_session(self, user_id: int) -> str:
        """새 세션 생성"""
        import uuid
        session_id = str(uuid.uuid4())
        
        session_data = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat()
        }
        
        self.redis.setex(
            f"session:{session_id}",
            self.session_ttl,
            json.dumps(session_data)
        )
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """세션 조회"""
        data = self.redis.get(f"session:{session_id}")
        return json.loads(data) if data else None
    
    def delete_session(self, session_id: str):
        """세션 삭제 (로그아웃)"""
        self.redis.delete(f"session:{session_id}")
```

### 세션 헬퍼 사용

```python
# account/adapter/input/web/session_helper.py

from fastapi import Request, HTTPException

async def get_current_user(request: Request) -> str:
    """현재 로그인한 사용자 ID 반환"""
    
    # 쿠키에서 세션 ID 추출
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    
    # Redis에서 세션 조회
    session_service = RedisSessionService()
    session = session_service.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=401, detail="세션이 만료되었습니다")
    
    return str(session["user_id"])
```

---

## 에러 처리

### 커스텀 예외 정의

```python
# common/exceptions.py

class DomainException(Exception):
    """도메인 계층 예외 베이스"""
    pass

class EntityNotFoundError(DomainException):
    """엔티티를 찾을 수 없음"""
    def __init__(self, entity_type: str, entity_id: int):
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} with id {entity_id} not found")

class ValidationError(DomainException):
    """검증 실패"""
    pass

class PermissionDeniedError(DomainException):
    """권한 없음"""
    pass
```

### 전역 예외 핸들러

```python
# app/main.py

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from common.exceptions import EntityNotFoundError, ValidationError, PermissionDeniedError

app = FastAPI()

@app.exception_handler(EntityNotFoundError)
async def entity_not_found_handler(request: Request, exc: EntityNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error": str(exc), "type": "entity_not_found"}
    )

@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": str(exc), "type": "validation_error"}
    )

@app.exception_handler(PermissionDeniedError)
async def permission_denied_handler(request: Request, exc: PermissionDeniedError):
    return JSONResponse(
        status_code=403,
        content={"error": str(exc), "type": "permission_denied"}
    )
```

---

## 다음 단계

- [프론트엔드 상세 가이드](./frontend-deep-dive.md)로 이동
- [메인 온보딩 가이드](./README.md)로 돌아가기
