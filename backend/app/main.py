import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.api.satellite import router as satellite_router
from app.api.weather import router as weather_router
from app.api.roads import router as roads_router

# Load environment variables from .env
load_dotenv()

app = FastAPI(
    title="NER Logistics Intelligence API",
    description="Backend API for environmental monitoring and resilient logistics in North Eastern India.",
    version="1.0.0"
)

# Enable CORS for frontend communication during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(satellite_router)
app.include_router(weather_router)
app.include_router(roads_router)

@app.get("/")
def read_root():
    """Root endpoint to verify the API server is alive."""
    return {
        "service": "NER Logistics Intelligence API",
        "status": "online",
        "version": "1.0.0"
    }

@app.get("/api/health")
def health_check():
    """Health check endpoint to verify backend operational readiness."""
    return {
        "status": "healthy",
        "service": "NER Logistics Intelligence",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "version": "1.0.0"
    }

