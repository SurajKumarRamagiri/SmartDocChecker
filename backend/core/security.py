"""
OAuth2 scheme definition shared across the app.

Note: tokenUrl is set to "/api/auth/login" to match the login endpoint.
The actual endpoint accepts JSON (not form-encoded OAuth2), so the Swagger
"Authorize" dialog won't work out-of-the-box; use the /api/auth/login
endpoint directly with {"email": ..., "password": ...}.
"""
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=True)
