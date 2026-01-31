# Troubleshooting Guide

## Common Issues and Solutions

### Installation Issues

#### Docker Compose Fails to Start

**Symptom**: `docker-compose up` fails with connection errors

**Possible Causes**:
1. Docker daemon not running
2. Port conflicts (5432, 8080 already in use)
3. Insufficient resources

**Solutions**:
1. Start Docker daemon: `sudo systemctl start docker`
2. Check ports: `netstat -tulpn | grep -E '5432|8080'`
3. Free up ports or change them in `docker-compose.yml`
4. Increase Docker resource limits in Docker Desktop settings

### Runtime Errors

#### "PostgreSQL Connection Failed"

**Symptom**: API returns 500 error with database connection error

**Diagnostic Steps**:
```bash
# Check if PostgreSQL container is running
docker ps | grep postgres

# Check PostgreSQL logs
docker logs repeatnomore_postgres

# Test connection
docker exec -it repeatnomore_postgres psql -U repeatnomore -c "SELECT 1;"
```

**Solutions**:
1. Restart PostgreSQL: `docker-compose restart postgres`
2. Clear and recreate volume:
   ```bash
   docker-compose down -v
   docker-compose up -d
   ```
3. Check network: `docker network inspect repeatnomore_network`

#### "Embedding Generation Timeout"

**Symptom**: Requests timeout after 30 seconds

**Possible Causes**:
1. Model not loaded
2. Insufficient memory
3. CPU overload

**Solutions**:
1. Pre-load model on startup
2. Increase timeout in configuration
3. Reduce batch size for embeddings
4. Add GPU support for faster processing
5. Monitor resources: `docker stats`

#### "LLM Response is Slow"

**Symptom**: Responses take >30 seconds to generate

**Optimization Steps**:
1. Use cloud LLM (Anthropic/OpenAI) instead of local Ollama
2. If using Ollama, enable GPU acceleration
3. Reduce context window size
4. Implement response streaming
5. Add response caching for common queries

### Query and Retrieval Issues

#### "No Relevant Documents Found"

**Symptom**: Every query returns "No relevant information found"

**Diagnostic Steps**:
```bash
# Check if documents are indexed
curl http://localhost:8080/api/health
```

**Solutions**:
1. Re-index documentation:
   ```bash
   curl -X POST http://localhost:8080/api/index
   ```
2. Lower similarity threshold in configuration
3. Verify documents are properly formatted
4. Check embedding model is working

#### Poor Answer Quality

**Symptom**: Answers are incorrect or irrelevant

**Improvement Steps**:
1. **Improve Documentation**:
   - Add more detailed examples
   - Include common edge cases
   - Update outdated information

2. **Tune Retrieval**:
   - Increase `top_k` for more context
   - Adjust chunk size and overlap
   - Lower minimum similarity score

### Performance Issues

#### High Memory Usage

**Symptom**: Container uses excessive memory

**Solutions**:
1. Limit model cache size
2. Use quantized embedding models
3. Implement caching
4. Set memory limits in docker-compose.yml:
   ```yaml
   deploy:
     resources:
       limits:
         memory: 4G
   ```

#### Slow Indexing

**Symptom**: Document indexing takes very long

**Optimizations**:
1. Process documents in parallel
2. Increase batch size for embeddings
3. Use GPU for embedding generation

### Database Issues

#### Vector Database Issues

**Symptom**: Queries fail with internal errors

**Recovery Steps**:
```bash
# Clear and recreate
docker-compose down -v
docker-compose up -d

# Re-index from source
curl -X POST http://localhost:8080/api/index
```

#### Disk Space Full

**Symptom**: "No space left on device" errors

**Solutions**:
1. Check space: `df -h`
2. Clear Docker resources:
   ```bash
   docker system prune -a
   docker volume prune
   ```
3. Increase disk allocation for Docker

## Debugging Tips

### Enable Debug Logging

Edit `.env`:
```bash
LOG_LEVEL=DEBUG
```

Restart services:
```bash
docker-compose restart app
```

### Access Container Shells

```bash
# App container
docker exec -it repeatnomore_app bash

# PostgreSQL container
docker exec -it repeatnomore_postgres psql -U repeatnomore
```

### Check Logs

```bash
# All logs
docker-compose logs -f

# Specific service
docker-compose logs -f app
docker-compose logs -f postgres

# Last 100 lines
docker-compose logs --tail=100 app
```

### Monitor Resources

```bash
# Container stats
docker stats

# Detailed monitoring
docker-compose top
```

## Getting Help

If you can't resolve the issue:

1. **Check Logs**: Always check logs first
2. **Search Issues**: Look for similar issues in GitHub
3. **Create Issue**: Include:
   - Error messages and logs
   - Docker version: `docker --version`
   - System info: `uname -a`
   - Steps to reproduce

## Preventive Maintenance

### Health Checks

```bash
#!/bin/bash
# healthcheck.sh

# Check API
curl -f http://localhost:8080/api/health || exit 1

# Check PostgreSQL
docker exec repeatnomore_postgres pg_isready -U repeatnomore || exit 1

echo "All services healthy"
```

### Backup Strategy

```bash
# Backup database
docker exec repeatnomore_postgres pg_dump -U repeatnomore repeatnomore > backup.sql

# Backup documentation
tar -czf backups/knowledge_base_$(date +%Y%m%d).tar.gz knowledge_base/

# Backup configuration
cp .env backups/.env.$(date +%Y%m%d)
```
