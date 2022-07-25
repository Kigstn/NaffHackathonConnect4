import random
from typing import Literal, Optional

import attrs
from naff import ActionRow, ComponentContext, Embed, InteractionContext, Message
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich import box

from core.misc import embed_message


_games: dict[int, "Connect4"] = {}


@attrs.define
class GameExists(Exception):
    game: "Connect4"


# todo random who starts first


@attrs.define(init=False)
class Connect4:
    ctx: InteractionContext = attrs.field()

    message: Message = attrs.field(init=False)

    _field: list[list[Literal["_", "O", "X"]]] = attrs.field(
        init=False,
        default=[
            ["X", "O", "_", "_", "_", "_", "_"],
            ["X", "O", "_", "_", "_", "_", "_"],
            ["X", "O", "_", "_", "_", "_", "_"],
            ["X", "O", "_", "_", "_", "_", "_"],
            ["X", "O", "_", "_", "_", "_", "_"],
            ["X", "O", "_", "_", "_", "_", "_"],
        ],
    )
    _player_turn: bool = attrs.field(init=False, default=random.choice([True, False]))

    def __init__(self, ctx: InteractionContext):
        # do not allow multiple games
        if game := _games.get(ctx.author.id):
            raise GameExists(game)
        self.__attrs_init__(ctx)

    @classmethod
    def get_existing(cls, ctx: ComponentContext) -> Optional["Connect4"]:
        return _games.get(ctx.author.id)

    async def play(self):
        # send initial message
        self.message = await self.ctx.send(
            embeds=self.get_embed(), components=self.get_components()
        )

    def get_embed(self) -> Embed:
        embed = embed_message(
            "Connect 4 Game",
            footer=f"{self.ctx.author.display_name}'s turn"
            if self._player_turn
            else "Computer is thinking...",
            member=self.ctx.author,
        )

        # which player is what
        console = Console()
        players = Text.assemble(
            ("⬤", "bold white"),
            " - Free\n",
            ("⬤", "bold blue"),
            f" - {self.ctx.author.display_name}\n",
            ("⬤", "bold red"),
            " - Computer",
        )
        with console.capture() as capture:
            console.print(players)
        players_text = capture.get()

        # create the game table
        game = Table(show_header=False, show_footer=False, box=box.HEAVY)
        for _ in range(7):
            game.add_column(justify="center", vertical="middle")
        for row in self._field:
            formatted = []
            for col in row:
                if col == "_":
                    formatted.append(Text("⬤", style="bold white"))
                elif col == "O":
                    formatted.append(Text("⬤", style="bold red"))
                elif col == "X":
                    formatted.append(Text("⬤", style="bold blue"))
            game.add_row(*formatted)

        # capture the ansi table
        with console.capture() as capture:
            console.print(game)
        table_text = "\n".join(capture.get().split("\n")[1:-2])

        embed.description = (
            f"""```ansi\n{players_text}\n```\n```ansi\n{table_text}\n```"""
        )
        return embed

    def get_components(self) -> ActionRow:
        return None
