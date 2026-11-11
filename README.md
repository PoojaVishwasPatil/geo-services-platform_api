# Geo Services Platform API (`geo-services-platform_api`)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16_PostGIS_3.4-336791.svg?style=flat&logo=postgresql&logoColor=white)](https://postgis.net/)
[![Redis](https://img.shields.io/badge/Redis-7_Alpine-DC382D.svg?style=flat&logo=redis&logoColor=white)](https://redis.io/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0_Async-D71F00.svg?style=flat&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)

High-performance, asynchronous geospatial REST API engine designed to query, search, and manage location-based services using PostgreSQL 16 + PostGIS 3.4 spatial indexing, Redis caching & sliding-window rate limiting, and JWT-authenticated administrative management.

🔗 **Frontend Repository:** [https://github.com/PoojaVishwasPatil/geo-services-platform](https://github.com/PoojaVishwasPatil/geo-services-platform)

---

## Architectural Highlights

- **Spatial Indexing & Geospatial Engine:** Utilizes PostGIS `geometry(Point, 4326)` with spatial GiST indexing and `ST_DistanceSphere` geodesic calculations for sub-millisecond radius filtering and distance sorting.
- **Async ASGI Architecture:** Built on FastAPI with asynchronous SQLAlchemy 2.0 and `asyncpg` connection pooling for non-blocking I/O.
- **Two-Tier Redis Integration:**
  - **Query Caching:** Caches spatial search results with configurable TTL and instantaneous cache invalidation upon create/update/delete mutations.
  - **Sliding-Window Rate Limiting:** Custom Redis sliding-window algorithm protecting public and administrative endpoints.
- **Admin Security Guard:** Stateless JWT authentication (HMAC-SHA256) with Bcrypt salted hashing protecting administrative CRUD endpoints.
- **Bulk Data Ingestion:** Transactional CSV and JSON file ingestion pipeline with coordinate bounds validation (`-90 <= lat <= 90`, `-180 <= lng <= 180`), phone format checks, and batch commits.

---

## API Documentation & Access Endpoints

Once the backend is running:
- **Interactive Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check Status:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

### Default Admin Credentials (Seeded)
- **Username:** `admin`
- **Password:** `AdminPassword123!`

---

## Tech Stack

- **Runtime & Framework:** Python 3.11+, FastAPI 0.111.0, Uvicorn (ASGI)
- **Database & ORM:** PostgreSQL 16 + PostGIS 3.4, SQLAlchemy 2.0 (Async), `asyncpg`, GeoAlchemy2, Shapely
- **Caching & Limiting:** Redis 7 (Alpine), `redis-py` async
- **Auth & Validation:** Pydantic v2, PyJWT, Passlib (Bcrypt)
- **Testing:** Pytest, Pytest-asyncio, HTTPX

---

## Quick Start & Local Setup

### 1. Prerequisites
- Python 3.11+
- Docker Desktop (for PostGIS & Redis)

### 2. Start PostgreSQL + PostGIS & Redis
Start the database and caching services using the included Docker Compose file:
```bash
docker compose up -d
```

Verify containers are running:
```bash
docker compose ps
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
- **Windows (PowerShell):** `Copy-Item .env.example .env`
- **Linux / macOS:** `cp .env.example .env`

### 4. Virtual Environment & Dependencies
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (CMD):
.\venv\Scripts\activate.bat
# Linux / macOS:
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Initialize Schema & Seed Data
Initialize PostGIS extensions, create tables, create the admin user, and seed sample geospatial data:
```bash
python -m scripts.seed_data
```

### 6. Run the Development Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Visit [http://localhost:8000/docs](http://localhost:8000/docs) to test endpoints interactively.

---

## Running Automated Tests

Run the full async test suite (Auth, Geospatial Services, Redis Caching, and Rate Limiting):
```bash
pytest -v
```

---

## Project Structure

```text
backend/
├── app/
│   ├── api/v1/          # REST route handlers (services, auth, admin, health)
│   ├── core/            # Configuration, security, Redis connection, rate limiting
│   ├── models/          # SQLAlchemy PostGIS ORM models (Service, User)
│   ├── repositories/    # Spatial queries and database access layer
│   ├── schemas/         # Pydantic v2 request/response validation schemas
│   └── main.py          # FastAPI application entrypoint & middleware setup
├── scripts/
│   ├── seed_data.py     # Database seeder & admin creator
│   ├── sample_services.csv
│   └── sample_services.json
├── tests/               # Pytest async test suite
├── Dockerfile           # Multi-stage production container build
├── docker-compose.yml   # PostGIS 16 & Redis 7 container configuration
├── requirements.txt     # Python package dependencies
└── pytest.ini           # Pytest async configuration
```

---

## Author & Maintainer

- **Developer:** Pooja Patil
- **GitHub:** [@PoojaVishwasPatil](https://github.com/PoojaVishwasPatil)
- **Email:** [poojapatil9579@gmail.com](mailto:poojapatil9579@gmail.com)
