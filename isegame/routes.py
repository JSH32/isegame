from quart import websocket

from isegame.game import ActionError, game_instance, GameStatus
from . import app


@app.route('/start', methods=['POST'])
async def start():
    try:
        result = await game_instance.start_game()
        return {"message": result.message}, result.status_code
    except ActionError as e:
        return {"message": e.message}, e.status_code

@app.route('/stop', methods=['POST'])
async def stop():
    try:
        result = await game_instance.stop_game()
        return {"message": result.message}, result.status_code
    except ActionError as e:
        return {"message": e.message}, e.status_code

@app.route('/running', methods=['GET'])
async def running():
    """Checks if the game is running."""
    return game_instance.current_game is not None

@app.websocket('/ws')
async def ws():
    """WebSocket route for handling user connection and actions."""
    connection = websocket._get_current_object()
    game_instance.connections.append(connection)
    try:
        user = None
        while True:
            try:
                data = await websocket.receive_json()
                if user is not None:
                    # Check correctness of question, send score and new question.
                    if game_instance.current_game and game_instance.current_game.status == GameStatus.ROUND:
                        if data["action"] == "answer":
                            correct = game_instance.current_game.validate_answer(user.id, data["answer"])

                            # Notify other clients of increased score
                            if correct:
                                await game_instance.broadcast_state()

                            question = game_instance.current_game.generate_question(user.id)
                            await connection.send_json({
                                'action': 'answer',
                                'correct': correct,
                                'question': question.to_dict()
                            })
                else:
                    # Join which only happens if the instance is not running.
                    if data["action"] == "join":
                        if game_instance.current_game:
                            raise ActionError("Game is already running")
                        
                        if data["piece"] in [u.piece for u in game_instance.users]:
                            raise ActionError("Someone is already using this piece")

                        user = await game_instance.add_user(data["name"], data["piece"], connection)
                        await connection.send_json({'action': 'identity', 'client': user.to_dict()})
                    elif data["action"] == "clients":
                        # Send clients specifically to the connection.
                        await connection.send_json({'action': 'clients', 'clients': [user.to_dict() for user in game_instance.users]})
                    # Other actions...
            except ActionError as e:
                await connection.send_json({'action': 'error', 'message': e.message})
    finally:
        await game_instance.remove_user(connection)
