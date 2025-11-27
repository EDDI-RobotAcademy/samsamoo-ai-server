import os

os.environ["CUDA_LAUNCH_BLOCKING"] = "1"
os.environ["TORCH_USE_CUDA_DSA"] = "1"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["NUMEXPR_MAX_THREADS"] = "16"

import logging
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

import warnings
warnings.filterwarnings("ignore")

from dotenv import load_dotenv
load_dotenv()

from anonymous_board.adapter.input.web.anonymous_board_router import anonymous_board_router
from board.adapter.input.web.board_router import board_router
from notice.adapter.input.web.notice_router import notice_router
from config.database.session import Base, engine

# Import all ORM models to ensure they are registered with SQLAlchemy's Base.metadata
# This must happen before Base.metadata.create_all() is called
from financial_statement.infrastructure.orm import (
    FinancialStatementORM, FinancialRatioORM, AnalysisReportORM, XBRLAnalysisORM
)

from documents.adapter.input.web.documents_router import documents_router
from documents_multi_agents.adapter.input.web.document_multi_agent_router import documents_multi_agents_router
from financial_statement.adapter.input.web.financial_statement_router import financial_statement_router
from financial_statement.adapter.input.web.xbrl_router import xbrl_router
from social_oauth.adapter.input.web.google_oauth2_router import authentication_router
from starlette.middleware.sessions import SessionMiddleware



# .env 불러오기
load_dotenv()



# 관리자 구글 이메일 리스트
ADMIN_GOOGLE_EMAILS = os.getenv("ADMIN_GOOGLE_EMAILS", "").split(",")

# FastAPI 앱 생성
from faq.adapter.input.web.faqs_router import faqs_router
from inquiry.adapter.input.web.inquiry_router import inquiry_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS 설정
origins = [
    "http://localhost:3000",  # Next.js 프론트 URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,   # 쿠키 허용
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔐 SessionMiddleware 추가 (핵심)
# secret_key는 .env 또는 임시 문자열 사용 가능
SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "dev-secret-key-1234")

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    same_site="lax",
    https_only=False  # 개발환경에서는 False, 운영에서는 True 권장
)

# 라우터 등록
app.include_router(anonymous_board_router, prefix="/anonymous-board")
app.include_router(authentication_router, prefix="/authentication")
app.include_router(board_router, prefix="/board")
app.include_router(documents_router, prefix="/documents")
app.include_router(documents_multi_agents_router, prefix="/documents-multi-agents")
app.include_router(notice_router, prefix="/notice")
app.include_router(financial_statement_router, prefix="/financial-statements")
app.include_router(faqs_router, prefix="/faqs")
app.include_router(inquiry_router, prefix="/inquiries")

app.include_router(xbrl_router, prefix="/xbrl")

# 앱 실행
if __name__ == "__main__":
    import uvicorn
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", 8000))

    # Base.metadata.drop_all(bind=engine)  # 필요 시 테이블 초기화
    Base.metadata.create_all(bind=engine)

    uvicorn.run(app, host=host, port=port)
