# SentryCache AI

> **Semantic Caching Gateway for LLM APIs with SQLite Persistence**

[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3.x-blue.svg)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

# Overview

SentryCache AI is a lightweight semantic caching gateway for Large Language Model (LLM) APIs.

Instead of caching exact prompts, it stores **embeddings** and retrieves responses based on semantic similarity. Similar user queries automatically reuse previous responses, significantly reducing API costs and improving latency.

It acts as a drop-in proxy in front of OpenAI-compatible APIs while persisting all cache entries in a lightweight SQLite database.

---

# Features

- Semantic caching using embeddings
- SQLite persistence (single database file)
- OpenAI API compatible
- REST API with FastAPI
- Configurable similarity threshold
- Cache hit/miss analytics
- Interactive Swagger documentation
- Mock mode for testing without API credits
- Easy deployment with zero external database dependencies
- Lightweight and production-friendly

---

# Architecture

```
                User Application
                       │
                       ▼
            SentryCache AI Gateway
                       │
        ┌──────────────┴──────────────┐
        │                             │
 Semantic Cache                 OpenAI API
 (SQLite + Embeddings)          (Only on cache miss)
        │
        ▼
 Cached Response
```

---

# Project Structure

```
sentrycache-ai/
│
├── app.py
├── cache.py
├── embeddings.py
├── database.py
├── demo.py
├── test_cache.py
├── requirements.txt
├── .env.example
├── LICENSE
├── README.md
└── sentry_cache.db
```

---

# Requirements

- Python 3.11 or 3.12
- pip
- Git (optional)

Python 3.13 is currently not officially supported.

---

# Installation

## Clone Repository

```bash
git clone https://github.com/parulxdev/sentrycache-ai.git

cd sentrycache-ai
```

---

## Create Virtual Environment

### Windows

```bash
python -m venv venv

venv\Scripts\activate
```

### macOS/Linux

```bash
python3 -m venv venv

source venv/bin/activate
```

---

## Install Dependencies

```bash
pip install --upgrade pip

pip install -r requirements.txt
```

---

# Configuration

Copy the example environment file.

Linux/macOS

```bash
cp .env.example .env
```

Windows

```cmd
copy .env.example .env
```

---

## Example `.env`

```env
# OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# Cache
CACHE_ENABLED=true
CACHE_SIMILARITY_THRESHOLD=0.90

# Server
PROXY_HOST=0.0.0.0
PROXY_PORT=8080

# Database
DB_PATH=sentry_cache.db

# Logging
LOG_LEVEL=INFO
```

---

# Environment Variables

| Variable | Description | Default |
|-----------|-------------|----------|
| OPENAI_API_KEY | OpenAI API Key | Required |
| CACHE_ENABLED | Enable semantic cache | true |
| CACHE_SIMILARITY_THRESHOLD | Similarity threshold | 0.90 |
| PROXY_HOST | Server host | 0.0.0.0 |
| PROXY_PORT | Server port | 8080 |
| DB_PATH | SQLite database path | sentry_cache.db |
| LOG_LEVEL | Logging level | INFO |

---

# Running the Server

Start the server:

```bash
python app.py
```

Example startup:

```
+-----------------------------------------------------------+
|             SentryCache AI - SQLite Version               |
|      Semantic caching with SQLite persistence             |
+-----------------------------------------------------------+

Database : sentry_cache.db
Proxy    : http://0.0.0.0:8080
Threshold: 0.90

Cache Stats

Total Queries : 0
Hits          : 0
Misses        : 0
Hit Rate      : 0%
Cache Size    : 0

API Docs

http://localhost:8080/docs

INFO: Uvicorn running on http://0.0.0.0:8080
```

---

## Run on Different Port

```bash
python app.py --port 8081
```

---

## Disable Cache

```bash
CACHE_ENABLED=false python app.py
```

---

## Debug Logging

Linux/macOS

```bash
LOG_LEVEL=DEBUG python app.py
```

Windows

```cmd
set LOG_LEVEL=DEBUG

python app.py
```

---

# API Endpoints

## Health Check

```
GET /
```

Returns server status.

---

## Chat Completions

```
POST /v1/chat/completions
```

Request

```json
{
  "prompt": "What is machine learning?"
}
```

---

### Cache Miss Response

```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Machine learning is a subset of AI..."
      }
    }
  ],
  "usage": {
    "total_tokens": 234,
    "cache_hit": false
  },
  "cache_stats": {
    "total_queries": 1,
    "hits": 0,
    "misses": 1,
    "hit_rate": 0,
    "cache_size": 1
  }
}
```

---

### Cache Hit Response

```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Machine learning is a subset of AI..."
      }
    }
  ],
  "usage": {
    "total_tokens": 0,
    "cache_hit": true,
    "similarity": 0.92
  },
  "cache_stats": {
    "total_queries": 2,
    "hits": 1,
    "misses": 1,
    "hit_rate": 50,
    "cache_size": 1
  }
}
```

---

# Cache Management Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| / | GET | Health check |
| /metrics | GET | Cache metrics |
| /cache/stats | GET | Detailed statistics |
| /cache/clear | POST | Clear cache |
| /cache/enable | POST | Enable caching |
| /cache/disable | POST | Disable caching |
| /docs | GET | Swagger UI |

---

# Testing

## Health Check

```bash
curl http://localhost:8080
```

---

## Send Query

```bash
curl -X POST http://localhost:8080/v1/chat/completions \
-H "Content-Type: application/json" \
-d '{"prompt":"What is machine learning?"}'
```

---

## Cache Metrics

```bash
curl http://localhost:8080/metrics
```

---

## Clear Cache

```bash
curl -X POST http://localhost:8080/cache/clear
```

---

# PowerShell

```powershell
$body = @{
    prompt = "What is machine learning?"
} | ConvertTo-Json

Invoke-WebRequest `
    -Uri http://localhost:8080/v1/chat/completions `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

---

# Demo

Interactive demo

```bash
python demo.py
```

Run tests

```bash
python test_cache.py
```

Full test suite

```bash
python test_cache.py full
```

---

# Swagger UI

Open:

```
http://localhost:8080/docs
```

Interactive API documentation is automatically generated by FastAPI.

---

# Performance Metrics

Available metrics:

| Metric | Description |
|---------|-------------|
| total_queries | Total requests |
| hits | Cache hits |
| misses | Cache misses |
| hit_rate | Cache hit percentage |
| cache_size | Number of cached entries |
| threshold | Similarity threshold |
| enabled | Cache enabled |

---

## Metrics Example

```json
{
  "total_queries": 49,
  "hits": 43,
  "misses": 6,
  "hit_rate": 87.75,
  "cache_size": 7,
  "threshold": 0.90,
  "enabled": true
}
```

---

# Performance Benefits

Typical improvements after warm cache:

| Metric | Without Cache | With Cache |
|---------|---------------|------------|
| API Calls | 100% | 10–30% |
| Latency | 1–5 sec | <100 ms |
| Cost | High | Reduced |
| Response Speed | Network dependent | Local SQLite |

---

# Troubleshooting

## Invalid API Key

```
401 Unauthorized
```

Verify:

```env
OPENAI_API_KEY=your_key
```

---

## SQLite Locked

Ensure only one process writes to the database simultaneously.

---

## Cache Not Working

Check:

```env
CACHE_ENABLED=true
CACHE_SIMILARITY_THRESHOLD=0.90
```

---

## Dependencies Missing

Reinstall packages:

```bash
pip install -r requirements.txt
```

---

# License

Licensed under the **MIT License**.

See the `LICENSE` file for details.

---

# Contributing

Contributions are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Commit your changes.
4. Push your branch.
5. Open a Pull Request.

---

# Author

**ParulXDev**

GitHub:
https://github.com/parulxdev

---

# Acknowledgements

- OpenAI
- FastAPI
- SQLite
- Python Community

---

## ⭐ Support

If you found this project useful, consider giving it a ⭐ on GitHub.
