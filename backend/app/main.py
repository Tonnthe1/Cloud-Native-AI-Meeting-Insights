from fastapi import FastAPI

app = FastAPI(title="AI Meeting Insights")

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/")
def read_root():
    return {"message": "Welcome to AI Meeting Insights"}
