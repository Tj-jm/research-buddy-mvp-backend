from fastapi import Request, HTTPException, status
from app.services.auth import decode_access_token

async def userProtect(request: Request, call_next):
    if request.url.path.startswith("/dashboard"):
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in")
        try:
            # only validate token presence/expiry
            decode_access_token(token)
        except:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return await call_next(request)

