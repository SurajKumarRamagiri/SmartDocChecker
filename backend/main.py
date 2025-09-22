# Document analysis endpoint
from fastapi import UploadFile, File
from typing import List
import time


import uvicorn
from fastapi import FastAPI, WebSocket, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import logging

app = FastAPI(title="SmartDocChecker API", description="Enterprise-grade contradiction detection API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# JWT Auth
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

class User(BaseModel):
    username: str
    role: str

class Document(BaseModel):
    id: str
    name: str
    status: str
    upload_date: str
    contradictions: List[str]

class Contradiction(BaseModel):
    id: str
    type: str
    description: str
    confidence: float
    document_id: str

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Replace with real user validation
    if form_data.username == "admin" and form_data.password == "admin":
        return {"access_token": "admin-token", "token_type": "bearer", "role": "admin"}
    elif form_data.username == "user" and form_data.password == "user":
        return {"access_token": "user-token", "token_type": "bearer", "role": "user"}
    else:
        raise HTTPException(status_code=400, detail="Invalid credentials")

@app.get("/users/me", response_model=User)
async def get_me(token: str = Depends(oauth2_scheme)):
    # Replace with real token decoding
    if token == "admin-token":
        return User(username="admin", role="admin")
    elif token == "user-token":
        return User(username="user", role="user")
    raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    # Save file and process
    logger.info(f"Received file: {file.filename}")
    return {"id": "doc1", "name": file.filename, "status": "pending", "upload_date": "2025-09-21", "contradictions": []}

@app.get("/documents", response_model=List[Document])
async def list_documents(token: str = Depends(oauth2_scheme)):
    # Return mock documents
    return [Document(id="doc1", name="Sample.pdf", status="completed", upload_date="2025-09-21", contradictions=["c1"])]

@app.get("/contradictions", response_model=List[Contradiction])
async def list_contradictions(token: str = Depends(oauth2_scheme)):
    # Return mock contradictions
    return [Contradiction(id="c1", type="temporal", description="Date mismatch", confidence=0.98, document_id="doc1")]

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Processing started...")
    await websocket.send_text("Processing completed!")
    await websocket.close()

@app.post("/api/analyze")
async def analyze_documents(files: List[UploadFile] = File(...)):
    start = time.time()
    # TODO: Replace with real AI analysis logic
    # For now, simulate analysis and return sample contradictions
    sample_contradictions = [
        {
            "type": "temporal",
            "severity": "high",
            "confidence": 94,
            "document1": {"name": files[0].filename if len(files) > 0 else "Doc1", "text": "Assignment submissions are due at 10:00 PM EST"},
            "document2": {"name": files[1].filename if len(files) > 1 else "Doc2", "text": "All assignments must be submitted by midnight (12:00 AM) EST"},
            "explanation": "Conflicting deadline times detected."
        },
        {
            "type": "requirement",
            "severity": "medium",
            "confidence": 87,
            "document1": {"name": files[0].filename if len(files) > 0 else "Doc1", "text": "Attendance at all lectures is mandatory for course completion"},
            "document2": {"name": files[1].filename if len(files) > 1 else "Doc2", "text": "Students may miss up to 2 lectures without penalty"},
            "explanation": "Contradictory attendance requirements."
        },
        {
            "type": "numerical",
            "severity": "high",
            "confidence": 96,
            "document1": {"name": files[1].filename if len(files) > 1 else "Doc2", "text": "Late submissions will incur a 5% penalty per day"},
            "document2": {"name": files[2].filename if len(files) > 2 else "Doc3", "text": "Late penalty is 10% per day for the first week"},
            "explanation": "Different penalty rates specified for late submissions."
        }
    ]
    avg_conf = round(sum(c["confidence"] for c in sample_contradictions) / len(sample_contradictions))
    analysis_time = f"{time.time() - start:.2f}s"
    return {
        "contradictions": sample_contradictions,
        "averageConfidence": avg_conf,
        "analysisTime": analysis_time
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
