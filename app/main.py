import os
import logging
import warnings
from dotenv import load_dotenv

# ---------------------------------
# 1) 환경 설정
# ---------------------------------
from starlette.staticfiles import StaticFiles

os.environ["CUDA_LAUNCH_BLOCKING"] = "1"
os.environ["TORCH_USE_CUDA_DSA"] = "1"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["NUMEXPR_MAX_THREADS"] = "16"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

warnings.filterwarnings("ignore")

load_dotenv()

# ---------------------------------
# 2) DB 모델 import 필수 (ORM 등록)
# ---------------------------------
from config.database.session import Base, engine

# Notice ORM 등록
from notice.domain.notice import Notice

# 금융 ORM들
from financial_statement.infrastructure.orm import (
    FinancialStatementORM,
    FinancialRatioORM,
    AnalysisReportORM,
    XBRLAnalysisORM,
)

# 다른 ORM 모델도 필요하면 여기 추가
# from board.infrastructure.orm.board_orm import BoardORM
# from inquiry.infrastructure.orm.inquiry_orm import InquiryORM
# ...

# ---------------------------------
# 3) 모든 테이블 생성 (ORM import 후!)
# ---------------------------------
Base.metadata.create_all(bind=engine)
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

# ---------------------------------
# 4) FastAPI App 생성
# ---------------------------------
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from utils.reports_path import get_reports_base_dir

app = FastAPI()
# 위에서 계산한 REPORTS_BASE_DIR와 동일 경로 사용
REPORTS_BASE_DIR = get_reports_base_dir()
print("[app] mount /static ->", REPORTS_BASE_DIR)  # 시작 로그

app.mount("/static", StaticFiles(directory=str(REPORTS_BASE_DIR)), name="static")
# CORS 설정
origins = [
    "http://localhost:3000",  # Next.js 프론트 URL
    "http://localhost:33333",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,         # 쿠키 허용 매우 중요
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------
# 6) 세션 쿠키 설정
# ---------------------------------
SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "dev-secret-key-1234")

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    same_site="lax",
    https_only=False      # 개발환경: False, 운영환경에서는 True 권장
)

# ---------------------------------
# 7) 모든 Router 등록
# ---------------------------------
from anonymous_board.adapter.input.web.anonymous_board_router import anonymous_board_router
from board.adapter.input.web.board_router import board_router
from notice.adapter.input.web.notice_router import notice_router
from documents.adapter.input.web.documents_router import documents_router
from documents_multi_agents.adapter.input.web.document_multi_agent_router import documents_multi_agents_router
from financial_statement.adapter.input.web.financial_statement_router import financial_statement_router
from financial_statement.adapter.input.web.xbrl_router import xbrl_router
from social_oauth.adapter.input.web.google_oauth2_router import authentication_router
from faq.adapter.input.web.faqs_router import faqs_router
from inquiry.adapter.input.web.inquiry_router import inquiry_router

# 라우터 연결
app.include_router(authentication_router, prefix="/authentication")
app.include_router(board_router, prefix="/board")
app.include_router(anonymous_board_router, prefix="/anonymous-board")
app.include_router(notice_router, prefix="/notice")
app.include_router(documents_router, prefix="/documents")
app.include_router(documents_multi_agents_router, prefix="/documents-multi-agents")
app.include_router(financial_statement_router, prefix="/financial-statements")
app.include_router(faqs_router, prefix="/faqs")
app.include_router(inquiry_router, prefix="/inquiries")
app.include_router(xbrl_router, prefix="/xbrl")

# ---------------------------------
# 8) 서버 실행
# ---------------------------------
if __name__ == "__main__":
    import uvicorn
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", 8000))
    uvicorn.run(app, host=host, port=port)
