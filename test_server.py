from fastapi import FastAPI
from fastapi.responses import FileResponse
app = FastAPI()
@app.get("/")
def test():
    open("/tmp/test.tsv", "w").write("test")
    return FileResponse("/tmp/test.tsv", filename="【HYTALE】.tsv")
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8123)
