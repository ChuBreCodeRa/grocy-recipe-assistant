# Performance Benchmarks

This document outlines performance expectations and behavior for the Grocy AI Recipe Assistant.

## Response Time Expectations

| Endpoint | Average Response Time | Peak Response Time | Notes |
|----------|----------------------|-------------------|-------|
| `/ai/suggest-recipes` | 1.5s - 4.5s | 6s - 9s | Varies based on inventory size, ingredient combinations, and AI filtering |
| `/feedback/submit` | 0.8s - 2.5s | 4s | AI review parsing is the primary bottleneck |
| `/inventory/sync` | 0.5s - 2s | 3s | Depends on Grocy inventory size |
| `/inventory` | 0.1s - 0.5s | 1s | Fast when database is properly indexed |

## Caching Strategy

The system implements Redis caching for several key operations:

| Operation | Cache TTL | Justification |
|-----------|-----------|---------------|
| Inventory data | 5 minutes | Balance freshness with reduced load on Grocy API |
| Spoonacular recipe searches | 24 hours | Recipe data rarely changes, high cache hit rate |
| AI ingredient filtering | 7 days | Stable classifications, high computational cost |
| AI ingredient combinations | 24 hours | Combinations for same ingredients are stable |
| User preferences | 30 minutes | Changes infrequently, but we want changes reflected relatively quickly |

## Resource Utilization

### Memory Usage
- Base system: ~200MB
- Per active user: ~5MB additional
- Redis cache (typical): 50-200MB depending on inventory size

### CPU Usage
- Idle: <1% of single core
- During API requests: 15-30% of single core
- During AI operations: 60-90% of single core briefly

### Network
- Spoonacular API: ~50-100KB per recipe search
- Grocy API: ~10-50KB per inventory sync
- OpenAI API: ~2-5KB per request

## Performance Optimizations

1. **Intelligent Ingredient Combinations**
   - Limits Spoonacular API calls through smarter ingredient grouping
   - Typical reduction: 60-70% fewer API calls compared to naive approach
   - AI-driven combinations produce 3x better recipe matches

2. **Redis Caching**
   - Cache hit rate for recipe searches: ~85%
   - Cache hit rate for ingredient combinations: ~90% 
   - Overall API cost reduction: ~75%

3. **Batch Processing**
   - User preference updates happen in nightly cron job
   - Reduces computational load during peak usage hours

4. **Simplified Output Option**
   - Mobile apps can request `simplified=true` parameter
   - Reduces response size by 60-70%
   - Improves mobile rendering performance

## Monitoring

Performance is monitored using:
- Backend response time logging
- Redis cache hit/miss metrics
- External API call timing
- Error rate tracking
- System resource utilization

## Scaling Considerations

The current architecture can handle ~100 concurrent users with the following limitations:
- Redis instance must be scaled as user count grows
- OpenAI API rate limits become a constraint at higher usage
- Spoonacular API pricing tier may need upgrading

---

## Related Docs

- [[SYSTEM_REQUIREMENTS]]
- [[API_REFERENCE]]
- [[DECISIONS]]
