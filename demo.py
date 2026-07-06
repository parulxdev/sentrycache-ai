#!/usr/bin/env python3
"""
SentryCache Demo - Interactive Demo
"""

import httpx
import time
import sys

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    HAS_COLOR = True
except:
    HAS_COLOR = False

def print_color(text, color="white"):
    if HAS_COLOR:
        colors = {
            'green': Fore.GREEN,
            'red': Fore.RED,
            'yellow': Fore.YELLOW,
            'blue': Fore.BLUE,
            'cyan': Fore.CYAN,
            'white': Fore.WHITE,
            'bold': Style.BRIGHT
        }
        print(colors.get(color, '') + text + Fore.RESET)
    else:
        print(text)

def run_demo():
    """Run interactive demo"""
    
    print_color("\n SentryCache AI - Interactive Demo", "cyan")
    print_color("=" * 60, "cyan")
    
    # Check if running
    try:
        resp = httpx.get("http://localhost:8080/")
        print_color(" SentryCache running!", "green")
        print(f" Cache Stats: {resp.json()['cache_stats']}")
    except:
        print_color(" SentryCache not running!", "red")
        print("   Start with: python app.py")
        return
    
    queries = [
        "What is RAG?",
        "Explain RAG briefly", 
        "Can you define RAG?",
        "What is Retrieval-Augmented Generation?",
        "Tell me about Python",
        "What is Python programming?",
        "How does RAG work?",
        "Explain RAG in simple terms"
    ]
    
    print_color("\n Testing 8 queries with cache...", "yellow")
    print("=" * 60)
    
    for i, query in enumerate(queries, 1):
        start = time.time()
        
        try:
            response = httpx.post(
                "http://localhost:8080/v1/chat/completions",
                json={"prompt": query},
                timeout=30.0
            )
            
            duration = (time.time() - start) * 1000
            result = response.json()
            
            # Check if cache hit
            cache_stats = result.get('cache_stats', {})
            hit_rate = cache_stats.get('hit_rate', 0)
            
            # Determine if this was a cache hit
            cache_hit = "similarity" in result.get('usage', {})
            
            if cache_hit:
                status = " CACHE HIT"
                color = "green"
            else:
                status = " LLM CALL"
                color = "red"
            
            print_color(f"{status} Query {i:2d}: {query[:40]}... {duration:.0f}ms", color)
            
        except Exception as e:
            print_color(f" Error: {e}", "red")
    
    # Get final metrics
    try:
        metrics = httpx.get("http://localhost:8080/metrics").json()
        print_color("\n" + "=" * 60, "cyan")
        print_color("📊 FINAL STATS", "cyan")
        print("=" * 60)
        print(f"Total Queries: {metrics['total_queries']}")
        print_color(f"Cache Hits: {metrics['hits']}", "green")
        print_color(f"Cache Misses: {metrics['misses']}", "red")
        print_color(f"Hit Rate: {metrics['hit_rate']:.1f}%", "yellow")
        print(f"Cache Size: {metrics['cache_size']}")
    except:
        pass
    
    print_color("\n Open API Docs: http://localhost:8080/docs", "blue")
    print_color(" Check metrics: http://localhost:8080/metrics", "blue")

if __name__ == "__main__":
    run_demo()