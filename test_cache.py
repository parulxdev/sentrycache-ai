
"""
SentryCache Test Suite
"""

import httpx
import time
import json

def test_semantic_cache():
    """Test semantic caching"""
    
    print(" Testing SentryCache\n")
    print("=" * 60)
    
    # Test queries
    test_cases = [
        {"query": "What is RAG?", "expected": "cache_miss"},
        {"query": "Explain RAG briefly", "expected": "cache_hit"},
        {"query": "What is Python?", "expected": "cache_miss"},
        {"query": "Define Python programming", "expected": "cache_hit"},
    ]
    
    results = []
    
    for test in test_cases:
        print(f"\n Query: {test['query']}")
        
        try:
            start = time.time()
            response = httpx.post(
                "http://localhost:8080/v1/chat/completions",
                json={"prompt": test['query']}
            )
            duration = (time.time() - start) * 1000
            
            result = response.json()
            cache_stats = result.get('cache_stats', {})
            
            # Check if cache hit
            is_cache_hit = cache_stats.get('hit_rate', 0) > 0
            
            if is_cache_hit:
                print(f"   CACHE HIT - {duration:.0f}ms")
                results.append(True)
            else:
                print(f"   CACHE MISS - {duration:.0f}ms")
                results.append(False)
                
        except Exception as e:
            print(f"   Error: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print(f"Tests Passed: {sum(results)}/{len(results)}")
    
    # Show final stats
    try:
        metrics = httpx.get("http://localhost:8080/metrics").json()
        print(f"\n Final Stats:")
        print(f"  Hit Rate: {metrics['hit_rate']:.1f}%")
        print(f"  Cache Size: {metrics['cache_size']}")
    except:
        pass

if __name__ == "__main__":
    test_semantic_cache()