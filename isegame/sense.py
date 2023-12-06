from sense_hat import SenseHat
import asyncio
from .game import game_instance, GameStatus

sense = SenseHat()

white = (255, 255, 255)
black = (0, 0, 0)

# Define play button (a triangle)isegame
play_button = [
    black, black, white, black, black, black, black, black,
    black, black, white, white, black, black, black, black,
    black, black, white, white, white, black, black, black,
    black, black, white, white, white, white, black, black,
    black, black, white, white, white, white, black, black,
    black, black, white, white, white, black, black, black,
    black, black, white, white, black, black, black, black,
    black, black, white, black, black, black, black, black
]

# Define pause button (two vertical lines)
pause_button = [
    black, black, black, black, black, black, black, black,
    black, white, black, black, black, black, white, black,
    black, white, black, black, black, black, white, black,
    black, white, black, black, black, black, white, black,
    black, white, black, black, black, black, white, black,
    black, white, black, black, black, black, white, black,
    black, white, black, black, black, black, white, black,
    black, black, black, black, black, black, black, black
]

# Define stop button (square)
stop_button = [
    black, black, black, black, black, black, black, black,
    black, white, white, white, white, white, white, black,
    black, white, white, white, white, white, white, black,
    black, white, white, white, white, white, white, black,
    black, white, white, white, white, white, white, black,
    black, white, white, white, white, white, white, black,
    black, white, white, white, white, white, white, black,
    black, black, black, black, black, black, black, black
]

async def sense_interface():
    """Returns the Sense Hat interface task."""
    while True:
        # Sense matrix display
        if game_instance.current_game:
            if game_instance.current_game.status == GameStatus.ROUND:
                sense.set_pixels(play_button)
            else:
                sense.set_pixels(pause_button)
        else:
            sense.set_pixels(stop_button)

        # Sense button presses
        for event in sense.stick.get_events():
            if event.action != "pressed":
                continue

            if event.direction == "up" and not game_instance.current_game or game_instance.current_game.status != GameStatus.ROUND:
                await game_instance.start_game()
            elif event.direction == "down" and game_instance.current_game:
                await game_instance.stop_game()

        await asyncio.sleep(1/120)
