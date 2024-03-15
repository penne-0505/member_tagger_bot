import datetime
from threading import Thread

import fastapi
import uvicorn

app = fastapi.FastAPI()

@app.get('/')
async def home():
    return "I'm alive"

def run():
    uvicorn.run(app, host='0.0.0.0', port=27250)

def keep_alive():
    t = Thread(target=run)
    t.start()
    print(f'[{datetime.datetime.now()}] Server is ready')