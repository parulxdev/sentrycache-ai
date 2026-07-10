
import os
import json
import time
import sqlite3
import hashlib
import logging
import numpy as np
from typing import Optional, Dict, List, Tuple
from contextlib import contextmanager
from dataclasses import dataclass
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import httpx
import uvicorn
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import openai

# ============ Load Environment ============

load_dotenv()

# ============ Configuration ============

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# DEBUG LINES:
if not OPENAI_API_KEY:
    OPENAI_API_KEY = "sk-proj-8X...YOUR-COMPLETE-KEY-HERE"
    print(" Using hardcoded API key (remove this in production)")

# Debug - check if key is loaded
print(f" API Key found: {OPENAI_API_KEY is not None}")
print(f" Key length: {len(OPENAI_API_KEY) if OPENAI_API_KEY else 0}")
if OPENAI_API_KEY:
    print(f" First 10 chars: {OPENAI_API_KEY[:10]}")



CACHE_SIMILARITY_THRESHOLD = float(os.getenv("CACHE_SIMILARITY_THRESHOLD", "0.90"))
DB_PATH = os.getenv("DB_PATH", "sentry_cache.db")
PROXY_HOST = os.getenv("PROXY_HOST", "0.0.0.0")
PROXY_PORT = int(os.getenv("PROXY_PORT", "8080"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
# ============ Logging ============

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)# This format is used to save CPU. Works regardless of order.
# Even if logging is disabled, the string is created! (wastes CPU)
#logger.info("User %s logged in", user_id)
# If logging is disabled, the string is NEVER created! (saves CPU)

logger = logging.getLogger(__name__)

# ============ SQLite Database ============

class CacheDatabase:
    """SQLite database for cache persistence"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()
        logger.info(f" Database initialized: {db_path}")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Cache entries table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cache_entries (
                    id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    response TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    timestamp REAL NOT NULL,
                    model TEXT DEFAULT 'gpt-3.5-turbo',
                    tokens INTEGER DEFAULT 0,
                    hits INTEGER DEFAULT 0
                )
            ''')
            
            # Statistics table (for metrics)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stats (
                    key TEXT PRIMARY KEY,
                    value INTEGER DEFAULT 0
                )
            ''')
            
            # Initialize stats if not present
            cursor.execute('''
                INSERT OR IGNORE INTO stats (key, value) VALUES 
                    ('total_queries', 0),
                    ('cache_hits', 0),
                    ('cache_misses', 0)
            ''')
            
            conn.commit()
            logger.info(" Database tables ready")
    
    def save_entry(self, entry_id: str, query: str, response: str, 
                   embedding: np.ndarray, model: str = "gpt-3.5-turbo", 
                   tokens: int = 0):
        """Save a cache entry"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Convert embedding to bytes
            embedding_bytes = embedding.astype(np.float32).tobytes()
            
            cursor.execute('''
                INSERT OR REPLACE INTO cache_entries 
                (id, query, response, embedding, timestamp, model, tokens, hits)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                entry_id, query, response, embedding_bytes, 
                time.time(), model, tokens, 0
            ))
            
            conn.commit()
            logger.info(f" Cached: {query[:50]}...")
    
    def search_similar(self, query_embedding: np.ndarray, threshold: float) -> Optional[Dict]:
        """Search for similar cached query using cosine similarity"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get all entries
            cursor.execute('''
                SELECT id, query, response, embedding, timestamp, hits
                FROM cache_entries
            ''')
            
            rows = cursor.fetchall()
            
            if not rows:
                return None
            
            best_match = None
            best_similarity = -1
            
            for row in rows:
                # Convert stored embedding back to numpy array
                stored_embedding = np.frombuffer(row['embedding'], dtype=np.float32)
                
                # Calculate cosine similarity
                similarity = self._cosine_similarity(query_embedding, stored_embedding)
                
                if similarity > threshold and similarity > best_similarity:
                    best_similarity = similarity
                    best_match = {
                        'id': row['id'],
                        'query': row['query'],
                        'response': row['response'],
                        'similarity': similarity,
                        'hits': row['hits'] + 1
                    }
            
            # Update hit count if match found
            if best_match:
                cursor.execute('''
                    UPDATE cache_entries SET hits = ? WHERE id = ?
                ''', (best_match['hits'], best_match['id']))
                conn.commit()
                
                # Update stats
                cursor.execute('''
                    UPDATE stats SET value = value + 1 WHERE key = 'cache_hits'
                ''')
                conn.commit()
                
                return best_match
            
            # Update miss stats
            cursor.execute('''
                UPDATE stats SET value = value + 1 WHERE key = 'cache_misses'
            ''')
            conn.commit()
            
            return None
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        if a is None or b is None:
            return 0.0
        
        # Ensure same dimensions
        if len(a) != len(b):
            return 0.0
        
        # Normalise
        a_norm = a / np.linalg.norm(a)
        b_norm = b / np.linalg.norm(b)
        
        # Cosine similarity
        similarity = np.dot(a_norm, b_norm)
        return float(similarity)
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get stats from stats table
            cursor.execute('SELECT key, value FROM stats')
            stats = {row['key']: row['value'] for row in cursor.fetchall()}
            
            # Get cache size
            cursor.execute('SELECT COUNT(*) as count FROM cache_entries')
            cache_size = cursor.fetchone()['count']
            
            total = stats.get('total_queries', 0)
            hits = stats.get('cache_hits', 0)
            misses = stats.get('cache_misses', 0)
            
            return {
                'total_queries': total,
                'hits': hits,
                'misses': misses,
                'hit_rate': (hits / total * 100) if total > 0 else 0,
                'cache_size': cache_size
            }
    
    def increment_total_queries(self):
        """Increment total query counter"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE stats SET value = value + 1 WHERE key = 'total_queries'
            ''')
            conn.commit()
    
    def clear_cache(self):
        """Clear all cache entries"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM cache_entries')
            cursor.execute('UPDATE stats SET value = 0 WHERE key = "cache_hits"')
            cursor.execute('UPDATE stats SET value = 0 WHERE key = "cache_misses"')
            conn.commit()
            logger.info("🗑️ Cache cleared")

# ============ Embedding Model ============

class EmbeddingModel:
    """Wrapper for sentence-transformers embedding model"""
    
    def __init__(self):
        logger.info(" Loading embedding model locally")
        try:
            self.model = SentenceTransformer(
                'all-MiniLM-L6-v2',
                local_files_only=True
            )
            logger.info(" Model loaded from local cache")
        except Exception as e:
            logger.warning(f"Local model not found: {e}")
            logger.info(" Downloading model once...")
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info(" Model downloaded and cached")
    
    def encode(self, text: str) -> np.ndarray:
        """Encode text to embedding vector"""
        return self.model.encode(text)

# ============ Semantic Cache ============

class SemanticCache:
    """Semantic cache using SQLite for persistence"""
    
    def __init__(self):
        self.db = CacheDatabase()
        self.embedder = EmbeddingModel()
        self.threshold = CACHE_SIMILARITY_THRESHOLD
        self.enabled = True
        
        logger.info(f" Cache threshold: {self.threshold}")
        logger.info(f" Database: {DB_PATH}")
    
    def search(self, query: str) -> Optional[Dict]:
        """Search for similar cached query"""
        if not self.enabled:
            return None
        
        try:
            # Generate embedding for query
            query_embedding = self.embedder.encode(query)
            
            # Search in database
            result = self.db.search_similar(query_embedding, self.threshold)
            
            if result:
                logger.info(f" Cache hit! Similarity: {result['similarity']:.2f}")
                return result
            
            logger.info(" Cache miss")
            return None
            
        except Exception as e:
            logger.error(f"Cache search error: {e}")
            return None
    
    def save(self, query: str, response: str, model: str = "gpt-3.5-turbo", tokens: int = 0):
        """Save query-response to cache"""
        if not self.enabled:
            return
        
        try:
            # Generate unique ID
            entry_id = hashlib.md5(query.encode()).hexdigest()
            
            # Generate embedding
            embedding = self.embedder.encode(query)
            
            # Save to database
            self.db.save_entry(entry_id, query, response, embedding, model, tokens)
            
        except Exception as e:
            logger.error(f"Cache save error: {e}")
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        return self.db.get_stats()
    
    def clear(self):
        """Clear all cache entries"""
        self.db.clear_cache()
    
    def increment_total_queries(self):
        """Increment total query counter"""
        self.db.increment_total_queries()

# ============ Initialize Cache ============

cache = SemanticCache()

# ============ FastAPI App ============

app = FastAPI(
    title="SentryCache AI (SQLite Version)",
    description="Semantic caching for LLM APIs with SQLite persistence",
    version="1.0.0"
)

# ============ Main Endpoint ============

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """Main endpoint with semantic caching"""
    start_time = time.time()
    try:
        # Parse request
        body = await request.json()
        query = body.get('prompt', '')
        
        if not query:
            return JSONResponse(
                status_code=400,
                content={"error": "No prompt provided"}
            )
        
        # Increment total queries
        cache.increment_total_queries()
        
        logger.info(f" Query: {query[:50]}...")
        
        # Check cache
        cache_start = time.time()
        cached = cache.search(query)
        
        cache_time = (time.time() - cache_start) * 1000
        
        if cached:
            logger.info(f" Cache lookup took {cache_time:.2f}ms")
            # CACHE HIT!
            total_time = (time.time() - start_time) * 1000
            logger.info(f"Total request time: {total_time:.2f}ms")
            

            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": cached['response']
                    }
                }],
                "usage": {
                    "total_tokens": 0,
                    "cache_hit": True,
                    "similarity": cached['similarity']
                },
                "cache_stats": cache.get_stats()
            }
        
        # CACHE MISS - Generate response (with fallback)
        logger.info(" Generating response...")
        
        answer = None
        tokens = 0
        used_mock = False
        
        # Try OpenAI first
        try:
            if OPENAI_API_KEY and OPENAI_API_KEY != "your_openai_api_key_here":
                client = openai.OpenAI(api_key=OPENAI_API_KEY)
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": query}],
                    temperature=0.7
                )
                answer = response.choices[0].message.content
                tokens = response.usage.total_tokens
                logger.info(" Using OpenAI")
            else:
                raise ValueError("OpenAI API key not configured")
                
        except Exception as e:
            logger.warning(f"OpenAI failed: {e}")
            logger.info(" Falling back to mock responses")
            used_mock = True
            
            # Mock responses (fallback)
            mock_responses = {
                "machine learning": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed.",
                "ml": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience.",
                "ai": "Artificial Intelligence (AI) is the simulation of human intelligence in machines that are programmed to think and learn.",
                "python": "Python is a high-level, interpreted programming language known for its simplicity and readability.",
                "rag": "RAG (Retrieval-Augmented Generation) is a technique that combines information retrieval with language generation for more accurate responses.",
                "llm": "LLM (Large Language Model) is a type of AI model trained on vast amounts of text data to understand and generate human-like language.",
                "cache": "Semantic caching stores responses based on meaning, so similar questions get the same answer without calling the API again.",
                "hello": "Hello! I am SentryCache AI. I can help you with questions about AI, machine learning, Python, and more.",
                "default": "I am a mock response. To get real AI responses, add your OpenAI API key to the .env file. For now, I am demonstrating the caching system."
            }
            
            # Find matching response
            answer = None
            for key, text in mock_responses.items():
                if key in query.lower():
                    answer = text
                    break
            
            if not answer:
                answer = mock_responses["default"]
            
            tokens = len(answer.split())
        
        # Save to cache (works with both real and mock)
        cache.save(query, answer, tokens=tokens)
        
        return {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": answer
                }
            }],
            "usage": {
                "total_tokens": tokens,
                "cache_hit": False,
                "used_mock": used_mock
            },
            "cache_stats": cache.get_stats()
        }
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# ============ Additional Endpoints ============

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "SentryCache AI (SQLite)",
        "version": "1.0.0",
        "status": "running",
        "cache_stats": cache.get_stats()
    }

@app.get("/metrics")
async def metrics():
    """Get cache metrics"""
    return cache.get_stats()

@app.post("/cache/clear")
async def clear_cache():
    """Clear all cache entries"""
    cache.clear()
    return {"status": "cleared", "message": "Cache cleared successfully"}

@app.get("/cache/stats")
async def cache_stats():
    """Detailed cache statistics"""
    stats = cache.get_stats()
    return {
        **stats,
        "threshold": cache.threshold,
        "enabled": cache.enabled
    }

@app.post("/cache/disable")
async def disable_cache():
    """Disable cache"""
    cache.enabled = False
    return {"status": "disabled", "message": "Cache disabled"}

@app.post("/cache/enable")
async def enable_cache():
    """Enable cache"""
    cache.enabled = True
    return {"status": "enabled", "message": "Cache enabled"}

# ============ Run ============

if __name__ == "__main__":
    print(f"""

   SentryCache AI             
        


Database: {DB_PATH}
Proxy: http://{PROXY_HOST}:{PROXY_PORT}
Cache Threshold: {CACHE_SIMILARITY_THRESHOLD}
Cache Stats: {cache.get_stats()}
API Docs: http://localhost:{PROXY_PORT}/docs

Single-user mode - no authentication required!
    """)
    
    uvicorn.run(
        app, 
        host=PROXY_HOST, 
        port=PROXY_PORT,
        log_level=LOG_LEVEL.lower()
    )