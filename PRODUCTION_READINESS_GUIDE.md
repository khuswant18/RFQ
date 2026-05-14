# SRIP Production Readiness Guide
## For Indian Steel Industry Deployment

**Last Updated:** May 13, 2026  
**Status:** Ready for Testing, Not Yet Production  
**Target Deployment:** 2-3 weeks

---

## Quick Start (Testing)

### 1. System is Already Running
```bash
# Backend: http://localhost:8000
# Frontend: http://localhost:5173
# API Docs: http://localhost:8000/docs
```

### 2. View Dashboard with Test Data
```bash
# Test data already generated
# Open: http://localhost:5173
# You should see 7 sample RFQs in various states
```

### 3. Test Upload Feature
```bash
# Go to: http://localhost:5173/upload
# Upload a PDF or image
# Watch it process through the pipeline
```

---

## What's Working ✅

1. **Core Pipeline** - All 7 agents implemented and working
2. **Dashboard** - Real-time RFQ feed with status tracking
3. **RFQ Detail Page** - Shows extraction, pricing, GST, quote
4. **File Upload** - PDF, images, text files accepted
5. **RAG System** - 408 documents embedded in ChromaDB
6. **Quote Generation** - PDF quotes with proper formatting
7. **Cost Calculation** - Material, logistics, margin, GST
8. **API Endpoints** - All documented in Swagger UI

---

## What's NOT Working ❌

### Critical Issues (Must Fix)

1. **No Database Persistence**
   - Data lost on server restart
   - Using in-memory JSON store
   - **Fix:** Implement PostgreSQL

2. **No WhatsApp Integration**
   - Twilio configured but webhook not wired
   - Can't receive RFQs from WhatsApp
   - **Fix:** Implement webhook handler

3. **No Email Integration**
   - IMAP polling not implemented
   - Can't receive RFQs from email
   - **Fix:** Implement email polling service

4. **No Authentication**
   - Anyone can access all RFQs
   - No user roles or permissions
   - **Fix:** Add JWT authentication

5. **No Input Validation**
   - Security risk (file upload, text input)
   - No file size limits
   - **Fix:** Add validation middleware

### High Priority Issues

6. **No Error Handling** - Agents fail silently
7. **No Logging/Monitoring** - Can't debug issues
8. **No Rate Limiting** - API vulnerable to abuse
9. **No API Documentation** - Swagger exists but incomplete
10. **No Environment Config** - Hardcoded values

---

## Production Deployment Checklist

### Phase 1: Database & Persistence (Week 1)

- [ ] Set up PostgreSQL database
- [ ] Create database schema
- [ ] Migrate from in-memory store to SQLAlchemy ORM
- [ ] Add database connection pooling
- [ ] Test data persistence (restart server, data still there)

**Estimated Time:** 2-3 days

### Phase 2: Authentication & Security (Week 1)

- [ ] Implement JWT authentication
- [ ] Create User and Role models
- [ ] Add permission checks to all endpoints
- [ ] Implement API key system
- [ ] Add input validation middleware
- [ ] Add file upload security (size limits, type validation)

**Estimated Time:** 2-3 days

### Phase 3: WhatsApp Integration (Week 2)

- [ ] Implement WhatsApp webhook endpoint
- [ ] Add message parsing (text, images)
- [ ] Add image download and storage
- [ ] Add response sending
- [ ] Test with Twilio sandbox
- [ ] Deploy to production Twilio

**Estimated Time:** 2-3 days

### Phase 4: Email Integration (Week 2)

- [ ] Implement IMAP polling service
- [ ] Add email parsing
- [ ] Add attachment extraction
- [ ] Add email response sending
- [ ] Test with Gmail/Outlook
- [ ] Deploy as background service

**Estimated Time:** 1-2 days

### Phase 5: Logging & Monitoring (Week 2)

- [ ] Implement structured logging
- [ ] Set up log aggregation (ELK or CloudWatch)
- [ ] Add performance metrics (Prometheus)
- [ ] Create monitoring dashboards (Grafana)
- [ ] Set up alerting (PagerDuty)

**Estimated Time:** 1-2 days

### Phase 6: Testing & QA (Week 3)

- [ ] End-to-end testing (upload → quote)
- [ ] WhatsApp integration testing
- [ ] Email integration testing
- [ ] Load testing (100+ RFQs/day)
- [ ] Security testing (penetration test)
- [ ] User acceptance testing (UAT)

**Estimated Time:** 2-3 days

### Phase 7: Deployment (Week 3)

- [ ] Set up Docker containers
- [ ] Configure Nginx reverse proxy
- [ ] Set up SSL/TLS certificates
- [ ] Deploy to production server
- [ ] Configure backups
- [ ] Set up disaster recovery

**Estimated Time:** 1-2 days

---

## Architecture for Production

```
┌─────────────────────────────────────────────────────────────┐
│                    PRODUCTION ARCHITECTURE                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  WhatsApp ──┐                                                │
│  Email ─────┼──► Nginx (Reverse Proxy) ──► FastAPI Backend  │
│  Web UI ────┘                                                │
│                                                               │
│  Backend Components:                                         │
│  ├─ API Server (FastAPI)                                    │
│  ├─ Agent Pipeline (7 agents)                               │
│  ├─ RAG System (ChromaDB)                                   │
│  ├─ Database (PostgreSQL)                                   │
│  ├─ Cache (Redis)                                           │
│  └─ Background Jobs (Celery)                                │
│                                                               │
│  External Services:                                          │
│  ├─ Groq API (LLM)                                          │
│  ├─ Serper API (Web Search)                                 │
│  ├─ Twilio (WhatsApp)                                       │
│  ├─ Gmail/Outlook (Email)                                   │
│  └─ AWS S3 (File Storage)                                   │
│                                                               │
│  Monitoring:                                                 │
│  ├─ ELK Stack (Logging)                                     │
│  ├─ Prometheus (Metrics)                                    │
│  ├─ Grafana (Dashboards)                                    │
│  └─ PagerDuty (Alerting)                                    │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Infrastructure Requirements

### Minimum (Small Deployment)
- 2 vCPU, 4GB RAM server
- PostgreSQL 13+
- Redis 6+
- 50GB storage

### Recommended (Medium Deployment)
- 4 vCPU, 8GB RAM server
- PostgreSQL 13+ (managed)
- Redis 6+ (managed)
- 200GB storage
- CDN for static files

### Enterprise (Large Deployment)
- Kubernetes cluster (3+ nodes)
- PostgreSQL 13+ (HA setup)
- Redis 6+ (cluster)
- 1TB+ storage
- Load balancer
- Auto-scaling

---

## Configuration for Production

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@db.example.com:5432/srip
REDIS_URL=redis://cache.example.com:6379/0

# API Keys
GROQ_API_KEY_1=gsk_xxx
GROQ_API_KEY_2=gsk_xxx
SERPER_API_KEY=xxx

# Twilio (WhatsApp)
TWILIO_ACCOUNT_SID=ACxxx
TWILIO_AUTH_TOKEN=xxx
TWILIO_WHATSAPP_NUMBER=whatsapp:+xxx

# Email
GMAIL_EMAIL=bot@company.com
GMAIL_PASSWORD=xxx
OUTLOOK_EMAIL=bot@company.com
OUTLOOK_PASSWORD=xxx

# AWS S3
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_S3_BUCKET=srip-quotes

# Application
ORIGIN_PINCODE=395006
DEFAULT_MARGIN_PERCENT=5.0
COMPANY_NAME=Your Company
COMPANY_GSTIN=24XXXXX1234Z5
CORS_ORIGINS=https://app.example.com,https://www.example.com

# Monitoring
SENTRY_DSN=https://xxx@sentry.io/xxx
LOG_LEVEL=INFO
```

---

## Testing Procedures

### 1. Unit Tests
```bash
cd backend
pytest tests/ -v
```

### 2. Integration Tests
```bash
# Test full pipeline
python -m pytest tests/test_pipeline.py -v
```

### 3. Load Testing
```bash
# Test with 100 concurrent requests
locust -f tests/locustfile.py --host=http://localhost:8000
```

### 4. Security Testing
```bash
# Run OWASP ZAP scan
zaproxy -cmd -quickurl http://localhost:8000 -quickout report.html
```

---

## Deployment Steps

### Using Docker Compose (Recommended)

```bash
# 1. Build images
docker-compose build

# 2. Start services
docker-compose up -d

# 3. Run migrations
docker-compose exec backend python -m alembic upgrade head

# 4. Seed data
docker-compose exec backend python backend/generate_test_data.py

# 5. Check health
curl http://localhost:8000/health
```

### Manual Deployment

```bash
# 1. Install dependencies
pip install -r backend/requirements.txt

# 2. Set environment variables
export DATABASE_URL=postgresql://...
export GROQ_API_KEY_1=gsk_...

# 3. Run migrations
python -m alembic upgrade head

# 4. Start backend
python backend/run.py

# 5. Start frontend (separate terminal)
cd frontend && npm run build && npm run preview
```

---

## Monitoring & Alerting

### Key Metrics to Monitor

1. **API Response Time** - Should be < 2 seconds
2. **Pipeline Success Rate** - Should be > 95%
3. **Database Connection Pool** - Should have available connections
4. **Redis Memory Usage** - Should be < 80% of limit
5. **Error Rate** - Should be < 1%
6. **WhatsApp Message Delivery** - Should be > 99%

### Alert Thresholds

- API response time > 5 seconds → Alert
- Pipeline success rate < 90% → Alert
- Database connection pool exhausted → Alert
- Redis memory > 90% → Alert
- Error rate > 5% → Alert
- WhatsApp delivery failure > 1% → Alert

---

## Troubleshooting Guide

### Issue: Dashboard shows "No RFQs"
**Solution:**
1. Check if backend is running: `curl http://localhost:8000/health`
2. Check if test data was generated: `python backend/generate_test_data.py`
3. Check browser console for errors (F12)
4. Check backend logs for errors

### Issue: Upload fails with "500 error"
**Solution:**
1. Check backend logs for error message
2. Verify file size < 50MB
3. Verify file type is PDF, image, or text
4. Check storage directory exists: `mkdir -p storage`

### Issue: Pipeline stuck in "processing"
**Solution:**
1. Check backend logs for agent errors
2. Verify Groq API key is valid
3. Check if Redis is running (if using Celery)
4. Restart backend service

### Issue: WhatsApp messages not received
**Solution:**
1. Verify Twilio credentials in .env
2. Check Twilio webhook URL is correct
3. Verify webhook endpoint is accessible
4. Check Twilio logs for errors

### Issue: Email not received
**Solution:**
1. Verify Gmail/Outlook credentials
2. Check email polling service is running
3. Verify email address is correct
4. Check spam folder

---

## Performance Optimization

### Database Optimization
- Add indexes on frequently queried columns
- Use connection pooling (pgbouncer)
- Archive old RFQs to separate table
- Regular VACUUM and ANALYZE

### API Optimization
- Enable response caching (Redis)
- Compress responses (gzip)
- Use CDN for static files
- Implement pagination for large result sets

### Agent Optimization
- Cache MCX prices (update every 15 min)
- Cache IS code lookups
- Parallelize agent execution
- Use async/await for I/O operations

---

## Backup & Disaster Recovery

### Daily Backups
```bash
# Backup database
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Backup files
tar -czf storage_backup_$(date +%Y%m%d).tar.gz storage/

# Upload to S3
aws s3 cp backup_*.sql s3://backups/
aws s3 cp storage_backup_*.tar.gz s3://backups/
```

### Recovery Procedure
```bash
# Restore database
psql $DATABASE_URL < backup_20260513.sql

# Restore files
tar -xzf storage_backup_20260513.tar.gz
```

---

## Support & Escalation

### Level 1: Self-Service
- Check documentation
- Check logs
- Restart service

### Level 2: Technical Support
- Contact: support@company.com
- Response time: 2 hours
- Available: 9 AM - 6 PM IST

### Level 3: Engineering
- Contact: engineering@company.com
- Response time: 30 minutes
- Available: 24/7 for critical issues

---

## Success Metrics

After production deployment, track these metrics:

| Metric | Target | Current |
|--------|--------|---------|
| RFQ Processing Time | < 60 seconds | N/A |
| Quote Accuracy | > 99% | N/A |
| System Uptime | > 99.5% | N/A |
| API Response Time | < 2 seconds | N/A |
| WhatsApp Delivery | > 99% | N/A |
| User Satisfaction | > 4.5/5 | N/A |
| Cost per Quote | < ₹5 | N/A |

---

## Next Steps

1. **This Week:**
   - [ ] Review this guide with team
   - [ ] Set up PostgreSQL database
   - [ ] Implement authentication

2. **Next Week:**
   - [ ] Implement WhatsApp webhook
   - [ ] Implement email integration
   - [ ] Set up monitoring

3. **Week 3:**
   - [ ] Complete testing
   - [ ] Deploy to staging
   - [ ] User acceptance testing

4. **Week 4:**
   - [ ] Deploy to production
   - [ ] Monitor closely
   - [ ] Gather feedback

---

## Questions?

For questions about this guide, contact:
- **Product:** product@company.com
- **Engineering:** engineering@company.com
- **Operations:** ops@company.com

---

**Document Version:** 1.0  
**Last Updated:** 2026-05-13  
**Next Review:** 2026-05-20
