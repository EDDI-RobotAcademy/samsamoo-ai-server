# API Reference

API documentation for SamSamOO-AI-Server.

## Interactive Documentation

- **Swagger UI**: http://localhost:33333/docs
- **ReDoc**: http://localhost:33333/redoc

## Endpoints Overview

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/authentication/google` | Initiate Google OAuth |
| GET | `/authentication/google/redirect` | OAuth callback |
| GET | `/authentication/status` | Check login status |
| POST | `/authentication/logout` | Logout user |

### Board (Authenticated)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/board/create` | Create board |
| GET | `/board/read/{id}` | Get board by ID |
| PUT | `/board/update/{id}` | Update board |
| DELETE | `/board/delete/{id}` | Delete board |
| GET | `/board/me` | Get user's boards |
| GET | `/board/list` | List all boards |

### Anonymous Board

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/anonymouse-board/create` | Create anonymous board |
| GET | `/anonymouse-board/list` | List anonymous boards |

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/documents/register` | Upload document |
| GET | `/documents/list` | List documents |

### Financial Statements

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/financial-statements/register` | Upload and analyze |
| GET | `/financial-statements/list` | List statements |
| GET | `/financial-statements/{id}` | Get statement details |

## Authentication

All authenticated endpoints require a session cookie. The session is established via Google OAuth flow.

### Cookie-based Session

```
Cookie: session_id=<uuid>
```

Sessions are stored in Redis with configurable TTL (default: 3600 seconds).

## Response Formats

### Success Response

```json
{
  "status": "success",
  "data": { ... }
}
```

### Error Response

```json
{
  "detail": "Error message"
}
```

## See Also

- [Getting Started](../guides/getting-started.md)
- [Architecture](../architecture/hexagonal.md)
