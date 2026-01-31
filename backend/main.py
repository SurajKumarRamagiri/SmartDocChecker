# Document analysis endpoint
from fastapi import UploadFile, File
from typing import List
import time,chardet


import uvicorn
from fastapi import FastAPI, WebSocket, Depends, HTTPException, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import logging
from ai_engine import detect_contradiction, semantic_similarity, extract_entities

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
async def analyze(files: list[UploadFile] = File(...)):
    texts = []
    for file in files:
        content = await file.read()
        detected = chardet.detect(content)
        encoding = detected['encoding']
        
        try:
            if encoding:
                text = content.decode(encoding)
            else:
                # Fallback to UTF-8 with error handling
                text = content.decode('utf-8', errors='ignore')
        except UnicodeDecodeError:
            # Handle as binary or skip
            text = content.decode('utf-8', errors='replace')
        
        texts.append(text)
    results = []
    for i in range(len(texts)):
        for j in range(i+1, len(texts)):
            contradiction = detect_contradiction(texts[i], texts[j])
            similarity = semantic_similarity(texts[i], texts[j])
            entities_i = extract_entities(texts[i])
            entities_j = extract_entities(texts[j])
            results.append({
                "doc_pair": [i, j],
                "contradiction_score": contradiction,
                "similarity_score": similarity,
                "entities_doc1": entities_i,
                "entities_doc2": entities_j
            })
    return {"contradictions": results}
