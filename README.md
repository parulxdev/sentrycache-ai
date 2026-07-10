#  SentryCache AI

> **Semantic Caching Gateway for LLM APIs with SQLite Persistence**

[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3.x-blue.svg)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

# Overview
SentryCache AI is a lightweight, semantic caching layer for LLM APIs that stores responses based on meaning rather than exact text matches. This dramatically reduces API costs and latency by serving cached responses for semantically similar queries.

The Problem: Every time you ask an AI a question, it costs money and takes 2-3 seconds.

The Solution: SentryCache remembers answers to similar questions and serves them instantly - for FREE!
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
- Lightweight 

---


