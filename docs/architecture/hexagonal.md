# Hexagonal Architecture

This project follows hexagonal (ports and adapters) architecture patterns.

## Overview

```
context_name/
├── domain/              # Business entities (pure Python)
├── application/
│   ├── port/           # Repository interfaces (abstract classes)
│   └── usecase/        # Business logic orchestration
├── infrastructure/
│   ├── orm/            # Database models (SQLAlchemy)
│   ├── repository/     # Port implementations
│   └── service/        # External service integrations
└── adapter/
    └── input/web/      # FastAPI routers (HTTP layer)
```

## Layer Responsibilities

### Domain Layer
- Pure Python classes with business logic
- No framework dependencies
- Entity definitions with validation rules

```python
# domain/financial_statement.py
class FinancialStatement:
    def __init__(self, company_name: str, ...):
        self.company_name = company_name

    def is_complete(self) -> bool:
        return self.normalized_data is not None
```

### Application Layer

#### Ports (Interfaces)
Abstract classes defining repository contracts:

```python
# application/port/financial_repository_port.py
from abc import ABC, abstractmethod

class FinancialRepositoryPort(ABC):
    @abstractmethod
    def save_statement(self, statement) -> FinancialStatement:
        pass
```

#### Use Cases (Business Logic)
Orchestrate domain operations through ports:

```python
# application/usecase/financial_analysis_usecase.py
class FinancialAnalysisUseCase:
    def __init__(self, repository: FinancialRepositoryPort):
        self.repository = repository  # Depends on abstraction

    def create_statement(self, ...):
        statement = FinancialStatement(...)
        return self.repository.save_statement(statement)
```

### Infrastructure Layer

#### ORM Models
Database-specific implementations:

```python
# infrastructure/orm/financial_statement_orm.py
from config.database.session import Base
from sqlalchemy import Column, Integer, String

class FinancialStatementModel(Base):
    __tablename__ = "financial_statements"
    id = Column(Integer, primary_key=True)
    company_name = Column(String(255))
```

#### Repository Implementations
Implement port interfaces:

```python
# infrastructure/repository/financial_repository_impl.py
class FinancialRepositoryImpl(FinancialRepositoryPort):
    def save_statement(self, statement):
        # SQLAlchemy implementation
        model = self._to_orm(statement)
        db.add(model)
        db.commit()
        return self._to_domain(model)
```

### Adapter Layer
HTTP interface (FastAPI routers):

```python
# adapter/input/web/financial_statement_router.py
from fastapi import APIRouter

router = APIRouter()

# Instantiate dependencies
repository = FinancialRepositoryImpl()
usecase = FinancialAnalysisUseCase(repository)

@router.post("/create")
async def create(request: CreateRequest, user_id = Depends(get_current_user)):
    return usecase.create_statement(...)
```

## Dependency Flow

```
Router → UseCase(port) ← Repository(implements port)
          ↓
        Domain
```

- **Router** knows UseCase and Repository implementation
- **UseCase** only knows Port interface (abstraction)
- **Repository** implements Port interface
- **Domain** has no external dependencies

## Key Principles

### Separation of Concerns
- Domain: Business rules only
- Application: Use case orchestration
- Infrastructure: Technical implementations
- Adapter: External interface handling

### Dependency Inversion
- High-level modules (use cases) don't depend on low-level modules (repositories)
- Both depend on abstractions (ports)

### Framework Independence
- Domain layer has no framework dependencies
- Infrastructure encapsulates all framework-specific code

## Bounded Contexts

```
SamSamOO-AI-Server/
├── account/               # User management
├── board/                 # Authenticated boards
├── anonymous_board/       # Public boards
├── documents/             # Document management
├── documents_multi_agents/# Multi-agent processing
├── financial_statement/   # Financial analysis
├── social_oauth/          # OAuth authentication
└── config/                # Shared configuration
```

Each context is self-contained with its own domain, application, infrastructure, and adapter layers.

## Korean Reference

헥사고날 아키텍처 구성:
- **domain**: 순수 비즈니스 엔티티 (JPA 의존성 없음)
- **application/usecase**: 비즈니스 시나리오 조율
- **application/port**: 레포지토리 인터페이스 정의
- **infrastructure/orm**: JPA/SQLAlchemy 엔티티
- **infrastructure/repository**: 포트 구현체
- **adapter/input/web**: HTTP 라우터 (컨트롤러)

도메인이 중심에 있고 외부 의존성과 분리되어 있어 변경에 유연함.
