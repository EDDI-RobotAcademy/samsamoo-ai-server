# Development Guide

Guidelines for developing and extending SamSamOO-AI-Server.

## Project Structure

```
SamSamOO-AI-Server/
├── app/                   # FastAPI application entry
├── config/                # Database, Redis configuration
├── account/               # User account context
├── board/                 # Authenticated boards context
├── anonymous_board/       # Public boards context
├── documents/             # Document management context
├── documents_multi_agents/# Multi-agent processing context
├── financial_statement/   # Financial analysis context
├── social_oauth/          # OAuth authentication context
├── scripts/               # Development scripts
├── docs/                  # Documentation
└── template/              # Code templates
```

## Adding a New Feature

### 1. Choose or Create Bounded Context

Each feature should belong to a bounded context following hexagonal architecture.

### 2. Create Domain Entity

```python
# my_context/domain/my_entity.py
class MyEntity:
    def __init__(self, name: str):
        self.name = name

    def validate(self) -> bool:
        return len(self.name) > 0
```

### 3. Define Port Interface

```python
# my_context/application/port/my_repository_port.py
from abc import ABC, abstractmethod

class MyRepositoryPort(ABC):
    @abstractmethod
    def save(self, entity) -> MyEntity:
        pass

    @abstractmethod
    def find_by_id(self, id: int) -> Optional[MyEntity]:
        pass
```

### 4. Implement Use Case

```python
# my_context/application/usecase/my_usecase.py
class MyUseCase:
    def __init__(self, repository: MyRepositoryPort):
        self.repository = repository

    def create(self, name: str) -> MyEntity:
        entity = MyEntity(name)
        return self.repository.save(entity)
```

### 5. Implement Repository

```python
# my_context/infrastructure/repository/my_repository_impl.py
class MyRepositoryImpl(MyRepositoryPort):
    def save(self, entity) -> MyEntity:
        model = MyModel(name=entity.name)
        db.add(model)
        db.commit()
        return entity
```

### 6. Create Router

```python
# my_context/adapter/input/web/my_router.py
from fastapi import APIRouter

router = APIRouter()
repository = MyRepositoryImpl()
usecase = MyUseCase(repository)

@router.post("/create")
async def create(name: str):
    return usecase.create(name)
```

### 7. Register Router

```python
# app/main.py
from my_context.adapter.input.web.my_router import router as my_router
app.include_router(my_router, prefix="/my-context")
```

## Development Scripts

Located in `scripts/` directory:

| Script | Purpose |
|--------|---------|
| `demo_llm_providers.py` | LLM provider demonstration |
| `test_pdf_generation.py` | PDF generation testing |
| `fix_fontconfig_warning.py` | Fontconfig fix (Windows) |

Run from project root:
```bash
python scripts/demo_llm_providers.py
```

## Testing

### Manual API Testing

Use `test_main.http` with HTTP client tools (VS Code REST Client, IntelliJ).

### Running Tests

```bash
pytest tests/
```

## Code Style

- Follow PEP 8 for Python code
- Use type hints for function signatures
- Keep domain entities pure (no framework dependencies)
- Use dependency injection via constructor

## See Also

- [Architecture](../architecture/hexagonal.md)
- [API Reference](../api/README.md)
- [Scripts README](../../scripts/README.md)
