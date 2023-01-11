import asyncio
import functools
import io
import json
import time
import zlib
from os import getenv

import uvicorn
from cryptography.fernet import Fernet, InvalidToken
from fastapi import FastAPI
from matplotlib import rcParams, style
from matplotlib.figure import Figure
from starlette.responses import StreamingResponse

# Matplotlib global styling

style.use("seaborn-dark")

rcParams.update({"font.size": 13})

for param in ["figure.facecolor", "axes.facecolor", "savefig.facecolor"]:
    rcParams[param] = "#2F3136"

for param in ["text.color", "axes.labelcolor", "xtick.color", "ytick.color"]:
    rcParams[param] = "1"


app = FastAPI()

SECRET = getenv("SECRET").encode()

IMAGE_FORMAT = "jpeg"


def generate_graph(*, colours: list[str], y_values: dict[str, list], fig_size: tuple, amount: int):
    fig = Figure(figsize=fig_size)

    axis = fig.add_subplot(1, 1, 1)

    axis.set_xlabel("Tests")

    axis.grid(color="#3A3C42")

    for i, (label, values) in enumerate(y_values.items()):
        x_values = range(0, amount, amount // len(values) + 1)

        axis.plot(
            x_values,
            values,
            label=label,
            marker="o",
            color=colours[i % len(colours)],
        )

    fig.legend(frameon=True)

    fig.tight_layout()

    buffer = io.BytesIO()

    fig.savefig(buffer, format=IMAGE_FORMAT)

    return buffer


@functools.lru_cache()
def handle_input(raw_data):
    try:
        decrypted = Fernet(SECRET).decrypt(raw_data.encode())
    except InvalidToken:
        return

    data = json.loads(zlib.decompress(decrypted).decode())

    until = data.pop("until", None)

    if until is None or until <= time.time():
        return

    return generate_graph(**data)


@app.get("/score_graph")
async def score_graph(raw_data: str):
    loop = asyncio.get_running_loop()

    args = functools.partial(handle_input, raw_data)

    buffer = await loop.run_in_executor(None, args)

    if buffer is None:
        return

    buffer.seek(0)

    return StreamingResponse(buffer, media_type=f"image/{IMAGE_FORMAT}")


uvicorn.run(app, host="0.0.0.0", port=8080)
