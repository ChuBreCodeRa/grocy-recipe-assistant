
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Grocy Recipe Assistant API is running"}
