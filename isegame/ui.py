import asyncio
import tkinter as tk
from tkinter import ttk
from .game import game_instance, GameStatus

class DebugGui(tk.Tk):
    def __init__(self, loop, interval=1/120):
        super().__init__()
        self.loop = loop
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.title("IseGame")
        self.tasks = []

        # Creating frame for a clean look 
        frame = tk.Frame(self)
        frame.pack(padx=10, pady=10)  # Space around the frame

        # Create the Start button
        self.start_button = tk.Button(
            frame,
            text="Start",
            command=lambda: asyncio.create_task(game_instance.start_game()), 
            bg="green", fg="white"
        )

        self.start_button.grid(row=0, column=0, padx=5, pady=5)  # Add to the grid

        # Create the Stop button
        self.stop_button = tk.Button(
            frame,
            text="Stop",
            command=lambda: asyncio.create_task(game_instance.stop_game()),
            bg="red", fg="white"
        )

        self.stop_button.grid(row=0, column=1, padx=5, pady=5)  # Add to the grid

        # Add a label for the timer
        self.timer_value = tk.StringVar()
        self.timer_label = tk.Label(frame, textvariable=self.timer_value, font=("Helvetica", 14))

        # Add label next to timer
        self.timer_text_label = tk.Label(frame, text="Timer: ", font=("Helvetica", 14))
        self.timer_text_label.grid(row=1, column=0, sticky="w")  # Add to the grid
        self.timer_label.grid(row=1, column=1, sticky="w")  # Add to the grid

        # Label for the game state
        self.state_value = tk.StringVar()
        self.state_label = tk.Label(frame, textvariable=self.state_value, font=("Helvetica", 14))

        # Add label next to state
        self.state_text_label = tk.Label(frame, text="State: ", font=("Helvetica", 14))
        self.state_text_label.grid(row=2, column=0, sticky="w")  # Add to the grid
        self.state_label.grid(row=2, column=1, sticky="w")  # Add to the grid

        tree_frame = tk.Frame(self)

        columns = ('id', 'name', 'piece', 'score')
        self.user_tree = ttk.Treeview(tree_frame, columns=columns, show='headings')

        # define headings
        self.user_tree.heading('id', text='ID')
        self.user_tree.heading('name', text='Name')
        self.user_tree.heading('piece', text='Piece')
        self.user_tree.heading('score', text='Score')

        self.user_tree.pack()
        tree_frame.pack()

        self.tasks.append(loop.create_task(self.updater(interval)))

    async def update_ui(self):
        self.user_tree.delete(*self.user_tree.get_children())
        for user in game_instance.users:
            score = game_instance.current_game.scores[user.id] if game_instance.current_game else 0
            user = (user.id, user.name, user.piece, score)
            self.user_tree.insert('', tk.END, values=user)

        self.timer_value.set(game_instance.timer)
        if game_instance.current_game:
            self.stop_button.config(state=tk.NORMAL)

            # When round playing start is invalid
            if game_instance.current_game.status == GameStatus.ROUND:
                self.state_value.set("Round")
                self.start_button.config(state=tk.DISABLED)
            else:
                self.state_value.set("Paused")
                self.start_button.config(state=tk.NORMAL)
        else:
            self.state_value.set("Not Started")
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
        

    async def updater(self, interval):
        while True:
            self.update()
            await self.update_ui()
            await asyncio.sleep(interval)

    def close(self):
        for task in self.tasks:
            task.cancel()
        self.destroy()
        self.loop.stop()
        self.loop.close()
