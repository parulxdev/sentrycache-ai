"""
SentryCache Test Suite
Tests semantic caching with proper cache hit detection
"""

import httpx
import time
import sys

BASE_URL = "http://localhost:8080"

def quick_test():
    """Quick test with just two queries to verify cache"""
    print("Quick Cache Test")
    print()
    print("=" * 60)
    
    print()
    print("1. Sending first query (should be CACHE MISS)...")
    try:
        response = httpx.post(
            f"{BASE_URL}/v1/chat/completions",
            json={"prompt": "What is machine learning?"},
            timeout=30.0
        )
        if response.status_code == 200:
            data = response.json()
            is_hit = data.get('usage', {}).get('cache_hit', False)
            if not is_hit:
                print("   PASS - MISS (expected)")
            else:
                print("   FAIL - HIT (unexpected)")
        else:
            print(f"   ERROR: {response.status_code}")
    except Exception as e:
        print(f"   ERROR: {e}")
        return
    
    time.sleep(1)
    
    print()
    print("2. Sending second query (should be CACHE HIT)...")
    try:
        response = httpx.post(
            f"{BASE_URL}/v1/chat/completions",
            json={"prompt": "Explain ML to me"},
            timeout=30.0
        )
        if response.status_code == 200:
            data = response.json()
            is_hit = data.get('usage', {}).get('cache_hit', False)
            similarity = data.get('usage', {}).get('similarity', 0)
            if is_hit:
                print(f"   PASS - CACHE HIT (Similarity: {similarity:.2f})")
            else:
                print("   FAIL - Expected CACHE HIT but got MISS")
        else:
            print(f"   ERROR: {response.status_code}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    print()
    print("=" * 60)
    print()
    print("Tip: Run 'python test_cache.py full' for complete test suite")

def full_test():
    """Full test suite with multiple queries"""
    
    print("Testing SentryCache - Full Suite")
    print()
    print("=" * 60)
    
    # Test queries grouped by topic
    test_cases = [
        # RAG queries
        {"query": "What is RAG?", "expected": "miss"},
        {"query": "Explain RAG briefly", "expected": "hit"},
        {"query": "Can you define RAG?", "expected": "hit"},
        {"query": "What is Retrieval-Augmented Generation?", "expected": "hit"},
        # Python queries
        {"query": "What is Python?", "expected": "miss"},
        {"query": "Define Python programming", "expected": "hit"},
        {"query": "Tell me about Python language", "expected": "hit"},
        # ML queries
        {"query": "What is machine learning?", "expected": "miss"},
        {"query": "Explain ML to me", "expected": "hit"},
    ]
    
    results = {"passed": 0, "failed": 0, "hits": 0, "misses": 0}
    
    print()
    print("Running Tests...")
    print()
    
    for i, test in enumerate(test_cases, 1):
        query = test['query']
        expected = test['expected']
        
        print(f"  {i}. Query: {query[:40]}{'...' if len(query) > 40 else ''}")
        
        try:
            start = time.time()
            response = httpx.post(
                f"{BASE_URL}/v1/chat/completions",
                json={"prompt": query},
                timeout=30.0
            )
            duration = (time.time() - start) * 1000
            
            if response.status_code == 200:
                result = response.json()
                is_hit = result.get('usage', {}).get('cache_hit', False)
                similarity = result.get('usage', {}).get('similarity', 0)
                used_mock = result.get('usage', {}).get('used_mock', False)
                
                # Track hits/misses
                if is_hit:
                    results["hits"] += 1
                else:
                    results["misses"] += 1
                
                # Determine if test passed
                if expected == "hit":
                    if is_hit:
                        status = "PASS - CACHE HIT"
                        results["passed"] += 1
                    else:
                        status = "FAIL - Expected HIT but got MISS"
                        results["failed"] += 1
                else:
                    if not is_hit:
                        status = "PASS - CACHE MISS (expected)"
                        results["passed"] += 1
                    else:
                        status = "FAIL - Expected MISS but got HIT"
                        results["failed"] += 1
                
                mock_indicator = " (Mock)" if used_mock else ""
                if is_hit:
                    print(f"     {status} - {duration:.0f}ms, Similarity: {round(similarity, 2)}{mock_indicator}")
                else:
                    print(f"     {status} - {duration:.0f}ms{mock_indicator}")
                
                # Show response preview
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                if content:
                    preview = content[:60] + ('...' if len(content) > 60 else '')
                    print(f"     Response: {preview}")
                
            else:
                print(f"     ERROR: HTTP {response.status_code}")
                results["failed"] += 1
                
        except httpx.ConnectError:
            print(f"     ERROR: Server not running! Start with: python app.py")
            sys.exit(1)
        except Exception as e:
            print(f"     ERROR: {str(e)[:100]}")
            results["failed"] += 1
        
        time.sleep(0.3)
    
    # Print summary
    total = results["passed"] + results["failed"]
    hit_rate = (results["hits"] / (results["hits"] + results["misses"]) * 100) if (results["hits"] + results["misses"]) > 0 else 0
    
    print()
    print("=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    print(f"  Passed:  {results['passed']}")
    print(f"  Failed:  {results['failed']}")
    print(f"  Hit Rate: {results['hits']}/{results['hits'] + results['misses']} ({hit_rate:.1f}%)")
    
    # Show cache stats
    print()
    print("=" * 60)
    print("CACHE STATISTICS")
    print("=" * 60)
    
    try:
        metrics = httpx.get(f"{BASE_URL}/metrics").json()
        print(f"  Total Queries: {metrics.get('total_queries', 0)}")
        print(f"  Cache Hits:    {metrics.get('hits', 0)}")
        print(f"  Cache Misses:  {metrics.get('misses', 0)}")
        print(f"  Hit Rate:      {metrics.get('hit_rate', 0):.1f}%")
        print(f"  Cache Size:    {metrics.get('cache_size', 0)}")
    except:
        print("  Could not fetch stats")
    
    print()
    print("=" * 60)
    print("Useful Links:")
    print(f"  API Docs: http://localhost:8080/docs")
    print(f"  Metrics:  http://localhost:8080/metrics")
    print(f"  Stats:    http://localhost:8080/cache/stats")
    print("=" * 60)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "full":
        full_test()
    else:
        quick_test()