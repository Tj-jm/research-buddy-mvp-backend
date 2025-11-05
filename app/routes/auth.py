from fastapi import APIRouter,Depends,Response,HTTPException, status, Request
from app.schemas.user import UserLogin, UserSignup
from app.core.auth import get_current_user
from app.services.auth import hash_password, verify_password, create_access_token, decode_access_token
from app.db import get_db

router = APIRouter()

# -------------------
# SIGN UP
# -------------------
@router.post("/signup")
async def signup(user: UserSignup,response:Response, db=Depends(get_db)):
    exists = await db.users.find_one({"email": user.email})
    if exists:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = hash_password(user.password)
    await db.users.insert_one({"email": user.email, "password": hashed_pw})
    #  Auto login on signup
    token = create_access_token({"sub": user.email})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,   # change to True in production HTTPS
        samesite="lax",
        max_age=3600
    )

    return {"msg": "User created & logged in"}

# -------------------
# LOGIN
# -------------------
@router.post("/login")
async def login(user: UserLogin, response: Response, db=Depends(get_db)):
    db_user = await db.users.find_one({"email": user.email})
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.email})
    # Store JWT in HttpOnly cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,   # set True in prod (HTTPS)
        samesite="lax",
        max_age=3600
    )
    return {"msg": "Logged in"}

# -------------------
# LOGOUT
# -------------------
@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"msg": "Logged out"}
# -------------------
# GET USER PROFILE
# -------------------

@router.get("/me")
async def me(user = Depends(get_current_user)):
    return {"email":user}
