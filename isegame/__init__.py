from http.client import NOT_FOUND
from hypercorn.config import Config
from hypercorn.asyncio import serve
import asyncio
from quart_schema import QuartSchema
from quart import Quart, jsonify, send_from_directory
import os
import argparse

app = Quart(__name__)
QuartSchema(app, convert_casing=True)

# Global error handler for all routes.
@app.errorhandler(Exception)
def handle_error(error):
    response = jsonify({"message": str(error)})
    response.status_code = 500
    return response

__import__(f"{__name__}.routes")

# Serve react app statically if this exists.
if os.path.exists("isegame_ui/dist"):
    @app.route("/<path:filename>")
    async def serve_react(filename: str):
        return await send_from_directory("isegame_ui/dist", filename)

    @app.route("/")
    async def serve_index():
        return await send_from_directory("isegame_ui/dist", "index.html")

    @app.errorhandler(NOT_FOUND)
    async def not_found(_):
        return await send_from_directory("isegame_ui/dist", "index.html")

parser = argparse.ArgumentParser()
parser.add_argument("--debug", action="store_true", help = "Run in debug mode")
parser.add_argument("--sense", action="store_true", help = "Run using sense hat as controller")
args = parser.parse_args()

# Start main application.
async def main() -> None:
    config = Config()
    config.accesslog = "-"
    config.bind = ["0.0.0.0:3000"]

    loop = asyncio.get_event_loop()

    if args.sense:
        from .sense import sense_interface
        loop.create_task(sense_interface())

    if args.debug:
        from . import ui
        ui.DebugGui(loop)

    await serve(app, config)

# Exists for task
def run() -> None:
    asyncio.run(main())