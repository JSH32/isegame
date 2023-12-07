import asyncio
from dataclasses import dataclass, field
from enum import Enum
from random import randint, shuffle
import time
from typing import List, NamedTuple, Optional, Dict
import uuid
from quart import Websocket


class ActionError(Exception):
    """Exception used to indicate an invalid action in the game."""
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code

class ActionResult(NamedTuple):
    """Structure representing the outcome of a game action."""
    message: str
    status_code: int

@dataclass
class Question:
    """Represents a question in the game."""
    question: str
    options: List[int]
    correct_answer: int
    timestamp: float

    def calculate_score(self):
        # Assumes that the score is higher the quicker the response
        time_elapsed = time.time() - self.timestamp
        return max(0, 10 - int(time_elapsed))  # Example scoring formula

    def to_dict(self):
        return {"question": self.question, "options": self.options}

    @classmethod
    def generate(cls):
        num1 = randint(1, 10)
        num2 = randint(1, 10)
        operation = randint(1, 3)  # 1: Addition, 2: Subtraction, 3: Multiplication
        if operation == 1:
            correct_answer = num1 + num2
            question = f"{num1} + {num2}"
        elif operation == 2:
            correct_answer = num1 - num2
            question = f"{num1} - {num2}"
        else:
            correct_answer = num1 * num2
            question = f"{num1} * {num2}"
        
        options = [correct_answer, correct_answer + randint(1, 4), correct_answer - randint(1, 4), correct_answer * randint(2, 3)]
        shuffle(options)
        
        return cls(question=question, options=options, correct_answer=correct_answer, timestamp=time.time())

@dataclass
class User:
    """Represents a user within the game."""
    id: uuid.UUID
    name: str
    piece: int
    connection: Websocket

    def to_dict(self):
        return {"id": str(self.id), "name": self.name, "piece": self.piece}

class GameStatus(Enum):
    ROUND = "round"
    PAUSED = "paused"

@dataclass
class GameState:
    # Last score from previous round, updated after calculation of how much to move forward
    last_scores: Dict[uuid.UUID, int] = field(default_factory=dict)
    scores: Dict[uuid.UUID, int] = field(default_factory=dict)
    questions: Dict[uuid.UUID, Question] = field(default_factory=dict)
    start_time: float = field(default=0)
    status: GameStatus = field(default=GameStatus.PAUSED)
    
    def to_dict(self):
        move_spaces = None
        max_moves_per_round = 5

        if self.status == GameStatus.PAUSED:
            move_spaces = {}

            # Two move algorithms due to skewed distribution of scores with less than 3 players.
            if len(self.scores) < 3:
                # Calculate moves based on score of each player seperately.
                for user_id, score in self.scores.items():
                    if user_id in self.last_scores:
                        delta_score = score - self.last_scores[user_id]
                        move_spaces[user_id] = min(max_moves_per_round, (delta_score // 6) + 1) if delta_score > 0 else 0
                    
                    else:
                        move_spaces[user_id] = min(max_moves_per_round, (score // 6) + 1) if score > 0 else 0

            else:
                # Calculate moves based on average score of all players.
                avg_score = sum(self.scores.values()) / max(1, len(self.scores.values()))
                for user_id, score in self.scores.items():
                    if user_id in self.last_scores:
                        delta_score = score - self.last_scores[user_id]
                        score_proportion = delta_score / avg_score if avg_score > 0 else 0
                        move_spaces[user_id] = round(max_moves_per_round * score_proportion)
                    else:
                        score_proportion = score / avg_score if avg_score > 0 else 0
                        move_spaces[user_id] = round(max_moves_per_round * score_proportion)

            for user_id, score in self.scores.items():
                self.last_scores[user_id] = score

        return {
            "scores": {str(user_id): score for user_id, score in self.scores.items()}, 
            "status": self.status, 
            "move_spaces": {str(user_id): spaces for user_id, spaces in move_spaces.items()} if move_spaces else None
        }
                
    def generate_question(self, user_id: uuid.UUID) -> Question:
        """Generates a new question for the given user."""
        new_question = Question.generate()
        self.questions[user_id] = new_question
        return new_question

    def validate_answer(self, user_id: uuid.UUID, answer_idx: int) -> bool:
        """Check if answer is correct, return score."""
        question = self.questions[user_id]

        if not question:
            return False
        
        answer = question.options[answer_idx]

        if user_id not in self.scores:
            self.scores[user_id] = 0

        if answer == question.correct_answer:
            score = question.calculate_score()
            self.scores[user_id] += score
            # Answer is correct
            return True
        else:
            # Answer is incorrect
            return False

class Game:
    """Class managing the game state, user connections and actions within the game."""
    users: List[User]
    connections: List[Websocket]
    current_game: Optional[GameState]
    timer: int
    timer_task: Optional[asyncio.Task]

    def __init__(self):
        self.users = []
        self.connections = []
        self.timer = 0
        self.current_game = None
        self.timer_task = None

    async def broadcast_state(self):
        state = self.current_game.to_dict()
        for user in self.users:
            await user.connection.send_json({'action': 'state', 'state': state})

    async def round_timer(self):
        self.timer = 30  # Duration of the round in seconds
        for remaining in range(self.timer, 0, -1):
            await asyncio.sleep(1)  # Wait for 1 second
            if self.current_game is None or self.current_game.status != GameStatus.ROUND:
                break

            self.timer = remaining

            # Send an update message with the timer status
            await self.broadcast_timer_update(remaining)
        
        # Final score
        self.timer = 0
        await self.broadcast_timer_update(0)

        if self.current_game is not None and self.current_game.status == GameStatus.ROUND:
            self.current_game.status = GameStatus.PAUSED
            await self.broadcast_state()
            self.current_game.last_scores = self.current_game.scores.copy()

    async def broadcast_timer_update(self, remaining_time):
        """Sends an update message with the timer status to all connections."""
        update = {
            'action': 'timer',
            'time': remaining_time,
        }

        for user in self.users:
            await user.connection.send_json(update)

    async def start_game(self) -> ActionResult:
        """Starts the game if there is no current game."""
        if self.current_game:
            if self.current_game.status == GameStatus.PAUSED:
                # If the game is paused, we prepare to continue.
                self.current_game.status = GameStatus.ROUND
            else:
                # If the game is running and not paused, we raise an error.
                raise ActionError("Game is already running")
        else:
            # If there is no current game, we start a new one.
            self.current_game = GameState()
            self.current_game.start_time = time.time()
            self.current_game.status = GameStatus.ROUND
            self.current_game.scores = {user.id: 0 for user in self.users}
            self.current_game.last_scores = {user.id: 0 for user in self.users}

        for user in self.users:            
            question = self.current_game.generate_question(user.id)
            await user.connection.send_json({'action': 'question', 'question': question.to_dict()})

        # Start or resume the background task to handle the round timer
        if self.timer_task is not None:
            self.timer_task.cancel()

        self.timer_task = asyncio.create_task(self.round_timer())

        await self.broadcast_state()

        msg = "New round has been started" if not hasattr(self, 'timer_task') else "Game has been resumed"
        return ActionResult(msg, 200)

    async def stop_game(self) -> ActionResult:
        """Stops the current game if there is one running."""

        if not self.current_game:
            raise ActionError("Game is not running")
        
        if self.timer_task is not None:
            self.timer = 0
            self.timer_task.cancel()
            await self.broadcast_timer_update(0)

        self.current_game = None
        for user in self.users:
            await user.connection.send_json({'action': 'stop'})
        
        return ActionResult("Game has been stopped", 200)

    async def add_user(self, name: str, piece: int, connection: Websocket) -> User:
        """Adds a new user to the game."""

        user = User(uuid.uuid4(), name, piece, connection)
        self.users.append(user)
        await self.broadcast_users_update()

        return user

    async def remove_user(self, connection: Websocket) -> None:
        """Removes a user from the game based on their connection."""

        user = next((u for u in self.users if u.connection == connection), None)
        if user:
            self.users.remove(user)
            await self.broadcast_users_update()
            if self.current_game:
                self.current_game.scores.pop(user.id, None)

    async def broadcast_users_update(self) -> None:
        """Sends an updated list of users to all connections."""

        users_list = [user.to_dict() for user in self.users]
        for conn in self.connections:
            await conn.send_json({'action': 'clients', 'clients': users_list})

# Global instance of the game server itself.
game_instance = Game()