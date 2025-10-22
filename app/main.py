from fastapi import FastAPI

app = FastAPI(title="Hedge Fund – minimal")

@app.get("/")
def root():
    return {"ok": True}

@app.get("/health")
def health():
    return {"ok": True} 