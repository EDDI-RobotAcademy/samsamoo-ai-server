# 🎯 SamSamOO AI Platform - 신규 개발자 온보딩 가이드

> AI 기반 재무제표 분석 플랫폼의 아키텍처와 코드 구조를 이해하기 위한 종합 가이드

## 📋 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [기술 스택](#기술-스택)
3. [아키텍처 개요](#아키텍처-개요)
4. [백엔드 구조](#백엔드-구조)
5. [프론트엔드 구조](#프론트엔드-구조)
6. [핵심 기능 흐름](#핵심-기능-흐름)
7. [개발 환경 설정](#개발-환경-설정)

---

## 프로젝트 개요

SamSamOO AI Platform은 **재무제표 PDF를 업로드하면 AI가 자동으로 분석하여 인사이트를 제공**하는 풀스택 웹 애플리케이션입니다.

### 주요 기능

| 기능 | 설명 |
|------|------|
| 📊 **재무제표 분석** | PDF 업로드 → 데이터 추출 → 재무비율 계산 → AI 인사이트 생성 |
| 📈 **XBRL 분석** | DART API 연동으로 상장사 재무정보 자동 조회 및 분석 |
| 📄 **문서 분석** | 멀티 에이전트 시스템으로 일반 문서 심층 분석 |
| 💬 **게시판** | 사용자 커뮤니티 (인증/익명) |
| 🔐 **인증** | Google OAuth 2.0 기반 소셜 로그인 |

### 모노레포 구조

```
Projects/
├── SamSamOO-AI-Server/   # 백엔드 (FastAPI + Python)
└── samsamoo-frontend/    # 프론트엔드 (Next.js 16 + React 19)
```

---

## 기술 스택

### 백엔드
```
Framework:     FastAPI + Uvicorn
Architecture:  헥사고날 (Hexagonal / Clean Architecture)
Database:      MySQL + SQLAlchemy ORM
Cache/Session: Redis
Auth:          Google OAuth 2.0
AI/ML:         OpenAI GPT, Anthropic Claude, LangChain
File Storage:  AWS S3
PDF 처리:      pdfplumber, camelot-py, pytesseract
```

### 프론트엔드
```
Framework:     Next.js 16 (App Router)
UI:            React 19 + Tailwind CSS 4
Language:      TypeScript (Strict Mode)
State:         React Context API
HTTP Client:   fetch API (native)
```

---

## 아키텍처 개요

### 전체 시스템 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                        클라이언트 (브라우저)                       │
│                    Next.js 프론트엔드 (localhost:3000)            │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼ HTTP (credentials: include)
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI 백엔드 (localhost:33333)             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                        Routers (어댑터 계층)               │   │
│  │   /authentication  /financial-statements  /xbrl  /board  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                   │                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                      Use Cases (응용 계층)                │   │
│  │        비즈니스 로직 - Port 인터페이스에만 의존               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                   │                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   Infrastructure (인프라 계층)            │   │
│  │   Repository 구현체 | 외부 서비스 (LLM, S3, DART API)      │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
         │              │                │              │
         ▼              ▼                ▼              ▼
      MySQL          Redis          AWS S3      OpenAI/Anthropic
    (데이터 저장)    (세션/캐시)     (파일 저장)      (AI 분석)
```

---

## 백엔드 구조

### 헥사고날 아키텍처란?

**헥사고날 아키텍처(Hexagonal Architecture)**는 비즈니스 로직을 외부 의존성(DB, API 등)으로부터 분리하는 설계 패턴입니다.

```
핵심 원칙: "의존성은 항상 안쪽(도메인)을 향한다"

┌─────────────────────────────────────────────────────────┐
│                    외부 세계 (웹, DB, API)                │
│  ┌───────────────────────────────────────────────────┐  │
│  │              어댑터 (Adapter) 계층                 │  │
│  │         Router, Repository 구현체, 외부 서비스      │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │           응용 (Application) 계층            │  │  │
│  │  │        UseCase, Port(인터페이스)             │  │  │
│  │  │  ┌───────────────────────────────────────┐  │  │  │
│  │  │  │           도메인 (Domain) 계층         │  │  │  │
│  │  │  │      순수 비즈니스 엔티티, 규칙          │  │  │  │
│  │  │  └───────────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 디렉토리 구조

각 바운디드 컨텍스트(기능 영역)는 동일한 구조를 따릅니다:

```
financial_statement/           # 재무제표 분석 컨텍스트
├── domain/                    # 📦 도메인 계층 (순수 Python)
│   ├── financial_statement.py # 재무제표 엔티티
│   ├── financial_ratio.py     # 재무비율 엔티티
│   └── analysis_report.py     # 분석 리포트 엔티티
│
├── application/               # 🎯 응용 계층
│   ├── port/                  # 인터페이스 정의 (추상 클래스)
│   │   ├── financial_repository_port.py
│   │   ├── pdf_extraction_service_port.py
│   │   └── llm_analysis_service_port.py
│   └── usecase/               # 비즈니스 로직
│       └── financial_analysis_usecase.py
│
├── infrastructure/            # 🔧 인프라 계층
│   ├── orm/                   # SQLAlchemy 모델
│   │   └── financial_statement_orm.py
│   ├── repository/            # Port 구현체
│   │   └── financial_repository_impl.py
│   └── service/               # 외부 서비스 연동
│       ├── pdf_extraction_service.py  # PDF 파싱
│       ├── llm_analysis_service.py    # AI 분석
│       └── llm_providers/             # LLM 제공자들
│           ├── openai_provider.py
│           ├── anthropic_provider.py
│           └── template_provider.py
│
└── adapter/                   # 🌐 어댑터 계층
    └── input/web/
        ├── financial_statement_router.py  # FastAPI 라우터
        ├── request/                       # 요청 DTO
        └── response/                      # 응답 DTO
```

### Port와 Adapter 패턴 이해하기

**Port (포트)** = 인터페이스 정의 (추상 클래스)
**Adapter (어댑터)** = 구현체

```python
# Port: 인터페이스 정의 (application/port/financial_repository_port.py)
from abc import ABC, abstractmethod

class FinancialRepositoryPort(ABC):
    """재무제표 저장소의 인터페이스 - UseCase는 이것만 알면 됨"""
    
    @abstractmethod
    def save_statement(self, statement: FinancialStatement) -> FinancialStatement:
        pass
    
    @abstractmethod
    def find_statement_by_id(self, statement_id: int) -> Optional[FinancialStatement]:
        pass
```

```python
# Adapter: 실제 구현 (infrastructure/repository/financial_repository_impl.py)
class FinancialRepositoryImpl(FinancialRepositoryPort):
    """MySQL을 사용한 저장소 구현체"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def save_statement(self, statement: FinancialStatement) -> FinancialStatement:
        orm_model = FinancialStatementORM.from_domain(statement)
        self.db.add(orm_model)
        self.db.commit()
        return orm_model.to_domain()
```

```python
# UseCase: Port에만 의존 (application/usecase/financial_analysis_usecase.py)
class FinancialAnalysisUseCase:
    """비즈니스 로직 - 인프라 구현체를 모름, Port만 앎"""
    
    def __init__(
        self,
        repository: FinancialRepositoryPort,      # 인터페이스에 의존
        pdf_service: PDFExtractionServicePort,    # 인터페이스에 의존
        llm_service: LLMAnalysisServicePort       # 인터페이스에 의존
    ):
        self.repository = repository
        self.pdf_service = pdf_service
        self.llm_service = llm_service
```

### 왜 이런 구조를 사용할까?

1. **테스트 용이성**: Port만 Mock하면 UseCase 단위 테스트 가능
2. **유연한 교체**: MySQL → PostgreSQL, OpenAI → Anthropic 교체가 쉬움
3. **관심사 분리**: 비즈니스 로직이 인프라에 오염되지 않음
4. **병렬 개발**: 인터페이스만 정하면 팀원들이 독립적으로 개발 가능

---

## 프론트엔드 구조

### Next.js App Router 구조

```
samsamoo-frontend/
├── app/                        # 📄 페이지 (App Router)
│   ├── layout.tsx              # 전역 레이아웃 (AuthProvider, Navbar 포함)
│   ├── page.tsx                # 홈페이지
│   ├── login/page.tsx          # 로그인 페이지
│   ├── financial-statements/   # 재무제표 기능
│   │   ├── list/page.tsx       # 목록 페이지
│   │   ├── create/page.tsx     # 생성 페이지
│   │   └── [id]/               # 동적 라우트
│   │       ├── page.tsx        # 상세 페이지
│   │       └── upload/page.tsx # PDF 업로드
│   └── xbrl-analysis/          # XBRL 분석 기능
│
├── components/                 # 🧩 재사용 컴포넌트
│   └── Navbar.tsx              # 네비게이션 바
│
├── contexts/                   # 🔄 전역 상태 관리
│   └── AuthContext.tsx         # 인증 상태 컨텍스트
│
├── features/                   # 🎯 기능별 코드
│   └── ...
│
└── types/                      # 📝 TypeScript 타입 정의
    └── ...
```

### AuthContext 이해하기

전역 인증 상태를 관리하는 React Context입니다:

```tsx
// contexts/AuthContext.tsx
"use client";

import { createContext, useContext, useState, useEffect } from "react";

interface AuthContextType {
    isLoggedIn: boolean;      // 로그인 상태
    refresh: () => void;      // 상태 갱신 함수
    logout: () => void;       // 로그아웃 함수
}

export const AuthProvider = ({ children }) => {
    const [isLoggedIn, setIsLoggedIn] = useState(false);

    // 로그인 상태 확인 (백엔드 API 호출)
    const refresh = () => {
        fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/authentication/status`, {
            credentials: "include",  // ⚠️ 중요: 쿠키 전송을 위해 필수
        })
        .then(res => res.json())
        .then(data => setIsLoggedIn(data.logged_in))
        .catch(() => setIsLoggedIn(false));
    };

    // 앱 최초 로딩 시 한 번 실행
    useEffect(() => {
        refresh();
    }, []);

    return (
        <AuthContext.Provider value={{ isLoggedIn, refresh, logout }}>
            {children}
        </AuthContext.Provider>
    );
};

// 컴포넌트에서 사용
export const useAuth = () => useContext(AuthContext);
```

### API 호출 패턴

**중요**: 백엔드와 통신 시 반드시 `credentials: "include"` 옵션을 포함해야 합니다. 이 옵션이 없으면 세션 쿠키가 전송되지 않아 인증이 작동하지 않습니다.

```typescript
// ✅ 올바른 예시
const response = await fetch(`${API_URL}/financial-statements/list`, {
    credentials: "include",  // 세션 쿠키 전송
});

// ❌ 잘못된 예시 - 인증이 작동하지 않음
const response = await fetch(`${API_URL}/financial-statements/list`);
```

---

## 핵심 기능 흐름

### 재무제표 분석 4단계 파이프라인

재무제표 분석의 핵심은 **4단계 파이프라인**입니다:

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Stage 1    │    │  Stage 2    │    │  Stage 3    │    │  Stage 4    │
│ PDF 추출    │ →  │ 비율 계산    │ →   │ AI 분석     │ →  │ 리포트 생성  │
│             │    │             │    │             │    │             │
│ pdfplumber  │    │ 재무비율     │    │ OpenAI/     │    │ PDF 차트    │
│ camelot     │    │ 공식 적용    │    │ Anthropic   │    │ 생성        │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

#### Stage 1: PDF 추출 (`pdf_extraction_service.py`)

```python
class PDFExtractionService:
    """PDF에서 재무 데이터 추출"""
    
    def extract_from_pdf(self, pdf_path: str) -> Dict[str, Any]:
        # 1차 시도: pdfplumber (구조화된 PDF에 적합)
        result = self._extract_with_pdfplumber(pdf_path)
        if self._has_sufficient_data(result):
            return result
        
        # 2차 시도: camelot (테이블 감지에 강함)
        result = self._extract_with_camelot(pdf_path)
        return result
    
    def normalize_to_kifrs(self, extracted_data: Dict) -> Dict:
        """추출된 데이터를 K-IFRS 표준 용어로 정규화"""
        # "자산총계" → "total_assets"
        # "매출액" → "revenue"
        # 등의 매핑 수행
```

#### Stage 2: 재무비율 계산 (`ratio_calculation_service.py`)

```python
class RatioCalculationService:
    """재무비율 계산"""
    
    def calculate_all_ratios(self, financial_data: Dict, statement_id: int):
        ratios = []
        
        # 수익성 비율
        ratios.append(self._calculate_roe(financial_data))      # ROE
        ratios.append(self._calculate_roa(financial_data))      # ROA
        ratios.append(self._calculate_profit_margin(financial_data))
        
        # 안정성 비율
        ratios.append(self._calculate_debt_ratio(financial_data))
        ratios.append(self._calculate_current_ratio(financial_data))
        
        return ratios
```

#### Stage 3: AI 분석 (`llm_analysis_service.py`)

```python
class LLMAnalysisServiceV2:
    """멀티 프로바이더 LLM 분석 서비스"""
    
    async def generate_complete_analysis(self, financial_data, ratios):
        # 3개 분석을 병렬로 실행 (성능 최적화)
        kpi_summary, table_summary, ratio_analysis = await asyncio.gather(
            self.generate_kpi_summary(financial_data, ratios),
            self.generate_statement_table_summary(financial_data),
            self.generate_ratio_analysis(ratios, financial_data)
        )
        
        return {
            "kpi_summary": kpi_summary,
            "statement_table_summary": table_summary,
            "ratio_analysis": ratio_analysis
        }
```

#### Stage 4: 리포트 생성 (`report_generation_service.py`)

```python
class ReportGenerationService:
    """PDF 리포트 및 차트 생성"""
    
    def generate_pdf_report(self, report, financial_data, ratios, chart_paths, output_path):
        # matplotlib으로 차트 생성
        # xhtml2pdf로 최종 PDF 리포트 생성
```

### 전체 UseCase 흐름

```python
# application/usecase/financial_analysis_usecase.py

class FinancialAnalysisUseCase:
    async def run_analysis_pipeline(self, statement_id: int) -> Dict[str, Any]:
        """4단계 분석 파이프라인 실행"""
        
        # 재무제표 조회
        statement = self.repository.find_statement_by_id(statement_id)
        
        try:
            # Stage 2: 재무비율 계산
            ratios = self.calculation_service.calculate_all_ratios(
                statement.normalized_data,
                statement_id
            )
            saved_ratios = self.repository.save_ratios(ratios)
            
        except Exception as e:
            # 비율 계산 실패 시 → LLM만으로 분석 진행 (graceful degradation)
            saved_ratios = []
        
        # Stage 3: AI 분석
        analysis_result = await self.llm_service.generate_complete_analysis(
            statement.normalized_data,
            saved_ratios
        )
        
        # Stage 4: 리포트 생성
        report_result = await self._generate_report(statement, saved_ratios, report)
        
        return {
            "statement": statement,
            "ratios": saved_ratios,
            "report": saved_report,
            "report_pdf_path": report_result["pdf_path"]
        }
```

---

## 개발 환경 설정

### 사전 요구사항

```bash
# 필수 소프트웨어
- Python 3.11+
- Node.js 18+
- MySQL 8.0+
- Redis 7.0+
- Ghostscript (PDF 테이블 추출용)
```

### 백엔드 설정

```bash
cd SamSamOO-AI-Server

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일 편집하여 DB, Redis, API 키 설정

# 서버 실행
python app/main.py
# → http://localhost:33333/docs 에서 Swagger UI 확인
```

### 프론트엔드 설정

```bash
cd samsamoo-frontend

# 의존성 설치
npm install

# 환경변수 설정
cp .env.example .env.local
# NEXT_PUBLIC_API_BASE_URL=http://localhost:33333

# 개발 서버 실행
npm run dev
# → http://localhost:3000 에서 확인
```

### 환경변수 예시

**백엔드 (.env)**:
```env
APP_HOST=0.0.0.0
APP_PORT=33333
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=samsamoo_db
MYSQL_USER=root
MYSQL_PASSWORD=your_password
REDIS_HOST=localhost
REDIS_PORT=6379
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
LLM_PROVIDER=auto
OPENAI_API_KEY=sk-xxx
```

**프론트엔드 (.env.local)**:
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:33333
```

---

## 다음 단계

1. **[백엔드 상세 가이드](./backend-deep-dive.md)** - UseCase 작성법, 새 기능 추가 방법
2. **[프론트엔드 상세 가이드](./frontend-deep-dive.md)** - 컴포넌트 패턴, 상태 관리
3. **[API 문서](http://localhost:33333/docs)** - Swagger UI에서 전체 API 확인

---

📧 문의사항이 있으면 팀 리더에게 연락하세요.
