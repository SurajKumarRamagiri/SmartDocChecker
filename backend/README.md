# SmartDocChecker Backend

## Features
- FastAPI async REST API with JWT authentication
- WebSocket endpoints for real-time updates
- PostgreSQL, Redis, Weaviate vector DB integration
- Celery for background AI processing
- XLM-RoBERTa, Sentence-BERT, spaCy NLP engine
- Database migrations with Alembic
- Dockerized microservices architecture

## Setup
1. Copy `.env` and update credentials as needed
2. Build and run services:
   ```sh
   docker-compose up --build
   ```
3. Run Alembic migrations:
   ```sh
   alembic upgrade head
   ```
4. Access API docs at `http://localhost:8000/docs`

## Development
- Main API: `main.py`
- Models: `models.py`
- AI Engine: `ai_engine.py`
- Celery Worker: `celery_worker.py`
- Database: `database.py`
- Redis: `redis_client.py`
- Vector DB: `vector_db.py`

## Running Locally ✅
Follow these steps to run the backend in development (Windows):

1. Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate
   ```
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Create an `.env` file (optional) with required environment variables (example):
   ```env
   DATABASE_URL=postgresql://user:password@localhost:5432/smartdocchecker
   REDIS_URL=redis://localhost:6379/0
   WEAVIATE_URL=http://localhost:8080
   ```
4. Start supporting services:
   - Using Docker (recommended):
     ```powershell
     docker-compose up -d db redis weaviate
     ```
   - Or run services locally (Postgres/Redis/Weaviate) separately.

5. Run migrations:
   ```powershell
   alembic upgrade head
   ```

6. Start Celery worker (optional):
   ```powershell
   celery -A celery_worker.celery_app worker --loglevel=info
   ```

7. Start the API with hot reload:
   ```powershell
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

8. Open the interactive docs:
   - http://localhost:8000/docs
   - Frontend dev server (Vite) typically runs at http://localhost:5173 - CORS is already configured.

## Running with Docker (📦)
Build and run all services:
```powershell
docker-compose up --build
```
This will expose the backend at `http://localhost:8000`.

## Testing (🧪)
Run unit tests:
```powershell
pytest
```

## Notes (💡)
- The project includes dummy JWT auth for development—replace with real auth in production.
- Adjust environment variables in `.env` or `docker-compose.yml` as required.

