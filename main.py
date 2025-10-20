from fastapi import FastAPI
import os

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

# --- opcionális: egyszerű teszt endpoint ---
@app.get("/")
def root():
    return {"ok": True, "service": "hedge-fund-core"}