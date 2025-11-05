from fastapi import Request, HTTPException, status
from app.services.auth import decode_access_token

async def get_current_user(request:Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not logged in")
    payload = decode_access_token(token)
    print(payload) # debugging purpose
    return payload["sub"]