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
