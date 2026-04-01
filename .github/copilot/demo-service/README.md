# Payments API Gateway

OrbitPay payment processing service.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Payments API Gateway                      │
├─────────────────────────────────────────────────────────────┤
│  POST /v1/transfers/standard  - Standard transfers (1-3 days)│
│  POST /v1/transfers/instant   - Instant transfers (TODO)     │
│  GET  /v1/accounts/{id}/balance                              │
└───────────┬────────────────┬────────────────┬───────────────┘
            │                │                │
            ▼                ▼                ▼
   ┌────────────────┐ ┌─────────────┐ ┌──────────────┐
   │  Redis Cache   │ │   Visa API  │ │  Payments DB │
   │   (Payments)   │ │  (Card Net) │ │   (Aurora)   │
   └────────────────┘ └─────────────┘ └──────────────┘
```

## Services

| Component | PagerDuty Service | Team |
|-----------|-------------------|------|
| Redis Cache | Redis Cache - Payments | OrbitPay NOC |
| Visa API | 3rd Party Card Networks | OrbitPay SRE |
| Database | Payments DB | OrbitPay SRE |

## Local Development

```bash
pip install -r requirements.txt
uvicorn payments_api.main:app --reload
```
