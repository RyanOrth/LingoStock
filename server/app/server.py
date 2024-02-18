from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from langserve import add_routes
from dotenv import load_dotenv

from app.QueryRunnable import QueryRunnable
# from app.AgiRunnableStable import AgiRunnable
from app.AgiRunnable import AgiRunnable

load_dotenv()

app = FastAPI()


@app.get("/")
async def redirect_root_to_docs():
    return RedirectResponse("/docs")


query_runnable = QueryRunnable()
add_routes(app, query_runnable, path="/query")

agi_runnable = AgiRunnable()
add_routes(app, agi_runnable, path="/agi")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
