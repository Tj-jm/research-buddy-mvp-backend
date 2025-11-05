from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import predict, auth, dashboard,  faculty_scrape,faculty_scrape_db
from app.middlewares.user_protect import userProtect
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Research Buddy Backend")

# CORS
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"], 
)

# Middleware for /dashboard/*
app.middleware("http")(userProtect)

# Routers
app.include_router(predict.router, prefix="/api", tags=["Prediction"])
app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(dashboard.router, prefix="/api", tags=["Dashboard"])
app.include_router(faculty_scrape.router, prefix="/api", tags=["Agent"])
app.include_router(faculty_scrape_db.router, prefix="/api", tags=["Faculty"])


@app.get("/")
def read_root():
    return {"message": "Research Buddy Backend is Running"}
