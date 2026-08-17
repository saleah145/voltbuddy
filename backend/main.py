import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models
from database import engine
from routers import appliances, grid, homes, simulations

app = FastAPI(title="VoltBuddy API")

models.Base.metadata.create_all(bind=engine)

try:
    with engine.connect():
        print("VoltBuddy database connected successfully!")
except Exception as error:
    print("Database connection failed:", error)

local_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]

production_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=local_origins + production_origins,
    allow_origin_regex=r"https://voltbuddy-[a-z0-9-]+-saleahjanee-4611s-projects\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(appliances.router)
app.include_router(homes.router)
app.include_router(grid.router)
app.include_router(simulations.router)
