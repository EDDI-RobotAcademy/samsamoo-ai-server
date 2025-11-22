# samsamoo-ai-server
samsamoo-ai-server



## first .env.local setting (The top-level package)
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


# start
 python -m app.main