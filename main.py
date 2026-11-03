from fastapi import FastAPI

app = FastAPI(title="Event Incident Platform")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}