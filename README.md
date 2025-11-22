# samsamoo-ai-server
samsamoo-ai-server

## .env.local setting (The top-level package)
`````
APP_HOST=0.0.0.0
APP_PORT=33333

AWS_ACCESS_KEY_ID=yourAccessKeyId
AWS_SECRET_ACCESS_KEY=yourSecretAccessKey
AWS_REGION=ap-northeast-2
AWS_S3_BUCKET=yourS3Bucket
MYSQL_USER=

MYSQL_PASSWORD=
MYSQL_HOST=
MYSQL_PORT=
MYSQL_DATABASE=

REDIS_HOST=
REDIS_PORT=
REDIS_DB=
REDIS_PASSWORD=

GOOGLE_CLIENT_ID=yourClientId
GOOGLE_CLIENT_SECRET=yourClientSecret
GOOGLE_REDIRECT_URI=http://localhost:33333/authentication/google/redirect
CLIENT_REDIRECT_URL=http://localhost:3000
SESSION_TTL_SECONDS=3600

`````

## install setting (프로젝트 cli 설치 등)
`````
1. 프로젝트별 인터프리터 설정(파이참)
- 상단 메뉴에서 File → Settings (단축키 Ctrl + Alt + S)
- 왼쪽 메뉴에서 Python Interpreter 클릭
- 오른쪽 상단에 인터프리터 추가 (로컬 인터프리터 추가) 
- 기존항목이나 새로 생성으로 conda로 설정!

2. pip install
pip install fastapi pymysql redis PyPDF2
pip install uvicorn
pip install tensorflow transformers
pip install torch torchvision

# 실행
python -m app.main
`````