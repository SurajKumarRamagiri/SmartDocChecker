from celery import Celery

celery_app = Celery('tasks', broker='redis://localhost:6379/0')

@celery_app.task
def process_document(document_id):
    # Placeholder for AI processing logic
    print(f"Processing document {document_id}")
    return True
