# backend/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth
from app.routers import inventory
from app.routers import production                   

app = FastAPI(
    title="CDI Food ERP",
    description="Order-to-Audit System for a Small Food Manufacturer",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(inventory.router) 
app.include_router(production.router)


@app.get("/")
def health_check():
    return {"status": "ok", "app": "CDI Food ERP"}