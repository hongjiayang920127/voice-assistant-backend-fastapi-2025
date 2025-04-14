from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware

# Use relative imports now
from .config import settings
from .logging_config import logger
from .database import get_db_session
from .api.v1.router import api_router
from .websocket.router import router as websocket_router

# Log application start
logger.info(f"Starting {settings.PROJECT_NAME}...")

app = FastAPI(
    # Use project name from settings
    title=settings.PROJECT_NAME,
    description="Backend API for the Voice Assistant project.",
    version="0.1.0",
    # Optional: Add OpenAPI URL prefix if desired
    # openapi_url=f"/api/v1/openapi.json"
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Handles any unhandled exception, logs it, and returns a generic 500 error.
    """
    logger.exception(f"Unhandled exception during request: {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"message": "An unexpected error occurred. Please try again later."},
    )

@app.get("/")
async def read_root():
    """
    Root endpoint to check if the API is running.
    """
    logger.info("Root endpoint accessed.")
    # You can also access settings here if needed
    # Example of raising an exception to test the handler:
    # if random.random() < 0.1: # Uncomment and import random to test
    #     raise ValueError("Something went wrong!")
    return {"message": f"{settings.PROJECT_NAME} is running!"}

# Database Health Check Endpoint
@app.get("/health/db")
async def health_check_db(db: AsyncSession = Depends(get_db_session)):
    """
    Checks the database connection by executing a simple query.
    """
    try:
        # Execute a simple query to check the connection
        result = await db.execute(text("SELECT 1"))
        if result.scalar_one() == 1:
            logger.info("Database health check successful.")
            return {"status": "ok", "message": "Database connection successful."}
        else:
            logger.error("Database health check failed: Unexpected query result.")
            # This case should ideally not happen with SELECT 1
            raise HTTPException(status_code=503, detail="Database health check failed: Unexpected result")
    except Exception as e:
        logger.exception("Database health check failed.")
        # Re-raise as HTTPException for FastAPI to handle
        raise HTTPException(status_code=503, detail=f"Database connection failed: {e}")

# Include the API router with the correct prefix
app.include_router(api_router, prefix=settings.API_V1_STR)

# Include the WebSocket router
app.include_router(websocket_router)

# This block allows running the app directly using `python app/main.py`
# For production, use a process manager like Gunicorn with Uvicorn workers.
if __name__ == "__main__":
    # Pass the app string so uvicorn can find the app object within the package
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True, 
        log_config=None 
    )