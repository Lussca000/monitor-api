from fastapi import FastAPI

from app.routers.monitors import router as monitors_router

app = FastAPI(
    title="HushMonitor",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(monitors_router)
