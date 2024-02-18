from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from langserve import add_routes

from app.LangChainRunnable import LangChainRunnable

app = FastAPI()


@app.get("/")
async def redirect_root_to_docs():
    return RedirectResponse("/docs")


langchain_runnable = LangChainRunnable()
add_routes(app, langchain_runnable, path="/langchain")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
