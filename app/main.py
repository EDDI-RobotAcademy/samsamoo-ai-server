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
from config.database.session import Base, engine
from documents.adapter.input.web.documents_router import documents_router
from documents_multi_agents.adapter.input.web.document_multi_agent_router import documents_multi_agents_router
from financial_statement.adapter.input.web.financial_statement_router import financial_statement_router
from social_oauth.adapter.input.web.google_oauth2_router import authentication_router

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = [
    "http://localhost:3000",  # Next.js 프론트 엔드 URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # 정확한 origin만 허용
    allow_credentials=True,      # 쿠키 허용
    allow_methods=["*"],         # 모든 HTTP 메서드 허용
    allow_headers=["*"],         # 모든 헤더 허용
)

app.include_router(anonymous_board_router, prefix="/anonymouse-board")
app.include_router(authentication_router, prefix="/authentication")
app.include_router(board_router, prefix="/board")
app.include_router(documents_router, prefix="/documents")
app.include_router(documents_multi_agents_router, prefix="/documents-multi-agents")
app.include_router(financial_statement_router, prefix="/financial-statements")

# 앱 실행
if __name__ == "__main__":
    import uvicorn
    host = os.getenv("APP_HOST")
    port = int(os.getenv("APP_PORT"))
    # Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    uvicorn.run(app, host=host, port=port)
