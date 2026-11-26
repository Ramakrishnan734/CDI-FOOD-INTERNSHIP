# backend/app/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth
from app.routers import inventory
from app.routers import production 
from app.routers import sales 
from app.routers import reports                    

app = FastAPI(
    title="CDI Food ERP",
    description="Order-to-Audit System for a Small Food Manufacturer",
    version="1.0.0"
)

allowed_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(inventory.router) 
app.include_router(production.router)
app.include_router(reports.router)
app.include_router(sales.router) 


@app.get("/")
def health_check():
    return {"status": "ok", "app": "CDI Food ERP"}