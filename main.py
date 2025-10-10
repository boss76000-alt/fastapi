from fastapi import FastAPI
app = FastAPI()

@app.get("/")
def root():
    return {"greeting": "Hello, World!", "message": "Welcome to FastAPI!"}

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/clearline")
def clearline():
    # ide jön majd a valós idejű logika / jelzés
    return {"status": "running", "signal": None}
