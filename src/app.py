from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .persistence import init_db
from .persistence.routes import router as persistence_router
from .review_api.routes import router as review_router
from .dashboard.routes import router as dashboard_router


app = FastAPI(
    title="SIH26099 Material Code Engine",
    description="AI-Driven Unified Material Master Platform Across CPSEs",
    version="1.0.0",
)

STATIC_DIR = Path(__file__).resolve().parent / "dashboard" / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
def startup():
    init_db()


# Tier 4: Persistence APIs
app.include_router(persistence_router)

# Tier 3: Human Review APIs
app.include_router(review_router)

# Tier 5: Dashboard & Analytics APIs
app.include_router(dashboard_router)


@app.get("/")
@app.get("/dashboard")
def serve_dashboard():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "project": "SIH26099 Material Code Engine",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {
        "project": "SIH26099 Material Code Engine",
        "status": "healthy",
    }