# Initialize Project

Run the following commands to set up and start the Jasque (Obsidian AI Agent) project locally.

## Prerequisites

- Docker Desktop installed and running
- UV package manager installed (`pip install uv` or `brew install uv`)

## 1. Create Environment File

```bash
cp .env.example .env
```

Creates your local environment configuration from the example template.

## 2. Install Dependencies

```bash
uv sync
```

Installs all Python packages defined in pyproject.toml.

## 3. Start Database

```bash
docker-compose up -d db
```

Starts PostgreSQL 18 in a Docker container on port 5433.

## 4. Wait for Database Health

```bash
docker-compose ps
```

Ensure the db container shows `(healthy)` status before proceeding.

## 5. Run Database Migrations

```bash
uv run alembic upgrade head
```

Applies all pending database migrations.

## 6. Start Development Server

```bash
uv run uvicorn app.main:app --reload --port 8123
```

Starts the FastAPI server with hot-reload on port 8123.

## 7. Validate Setup

In a new terminal, check that everything is working:

```bash
# Test API health
curl -s http://localhost:8123/health

# Test database connection
curl -s http://localhost:8123/health/db
```

Both should return `{"status":"healthy",...}` responses.

## Access Points

- Swagger UI: http://localhost:8123/docs
- Health Check: http://localhost:8123/health
- Database Health: http://localhost:8123/health/db
- PostgreSQL: localhost:5433

## Cleanup

To stop services:

```bash
# Stop dev server: Ctrl+C in the terminal running uvicorn

# Stop database
docker-compose down

# Stop database and remove data volume
docker-compose down -v
```

## Troubleshooting

**Port 5433 in use:**
```bash
# Check what's using the port
lsof -i :5433
# Kill if needed, or change POSTGRES port in docker-compose.yml
```

**Database connection failed:**
```bash
# Ensure database is healthy
docker-compose ps
# Check logs
docker-compose logs db
```
