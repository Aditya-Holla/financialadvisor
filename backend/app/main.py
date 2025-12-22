from fastapi import FastAPI

app = FastAPI(title="Financial Advisor Backend")

@app.get("/health")
def health_check():
    return {"status": "ok"}
