import asyncio
import copy
import logging
import random
from typing import Literal, Optional

import attrs
from naff import (
    Button,
    ButtonStyles,
    ComponentContext,
    Embed,
    InteractionContext,
    Member,
    Message,
)
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
    pvp: bool = attrs.field()
    to_win: int = attrs.field(default=4)

    message: Message = attrs.field(init=False)
    logger = attrs.field(init=False, default=logging.getLogger("Connect4"))
    lock = attrs.field(init=False, default=asyncio.Lock())

    _field: list[list[Literal["_", "O", "X"]]] = attrs.field(init=False)
    _cursor_position: int = attrs.field(default=0)
    _components: list[Button] = attrs.field(init=False)
    _player_one_turn: bool = attrs.field(
        init=False, default=random.choice([True, False])
    )

    def __init__(self, ctx: InteractionContext, *args, **kwargs):
        # do not allow multiple games
        if game := _games.get(ctx.author.id):
            raise GameExists(game)
        self.__attrs_init__(ctx, *args, **kwargs)

    def __attrs_post_init__(self):
        self._field = [
            ["X", "O", "_", "_", "_", "_", "_"],
            ["X", "O", "_", "_", "_", "_", "_"],
            ["X", "O", "_", "_", "_", "_", "_"],
            ["X", "O", "_", "_", "_", "_", "_"],
            ["X", "O", "_", "_", "_", "_", "_"],
            ["X", "O", "_", "_", "_", "_", "_"],
        ]
        self._components = [
            Button(
                custom_id=f"{self.ctx.author.id}|left_full",
                style=ButtonStyles.BLUE,
                label="«",
            ),
            Button(
                custom_id=f"{self.ctx.author.id}|left_one",
                style=ButtonStyles.BLUE,
                label="‹",
            ),
            Button(
                custom_id=f"{self.ctx.author.id}|submit",
                style=ButtonStyles.BLUE,
                label="🢃",
            ),
            Button(
                custom_id=f"{self.ctx.author.id}|right_one",
                style=ButtonStyles.BLUE,
                label="›",
            ),
            Button(
                custom_id=f"{self.ctx.author.id}|right_full",
                style=ButtonStyles.BLUE,
                label="»",
            ),
        ]

    @classmethod
    def get_existing(cls, author_id: int) -> Optional["Connect4"]:
        return _games.get(author_id)

    async def play(self):
        _games[self.ctx.author.id] = self

        # send initial message
        self.message = await self.ctx.send(
            embeds=self.get_embed(), components=self.get_components()
        )

        # make the pvp turn if that is next
        if self.pvp and not self._player_one_turn:
            await self.computer_turn(symbol="O")

    def get_embed(
        self, winning_coords: Optional[list[tuple[int, int]]] = None
    ) -> Embed:
        if winning_coords is None:
            winning_coords = []

        embed = embed_message(
            "Connect 4 Game",
            footer=f"{self.ctx.author.display_name}'s turn"
            if self._player_one_turn
            else "Computer is thinking...",
            member=self.ctx.author,
        )
        if winning_coords:
            embed.set_footer(
                f"{self.ctx.author.display_name} won!"
                if not self._player_one_turn
                else "Computer won!"
            )

        # which player is what
        console = Console()
        players = Text.assemble(
            ("⬤", "white"),
            " - Free\n",
            ("⬤", "blue"),
            f" - {self.ctx.author.display_name}\n",
            ("⬤", "red"),
            " - Computer",
        )
        with console.capture() as capture:
            console.print(players)
        players_text = capture.get()

        # create the tables
        game = Table(show_header=False, show_footer=False, box=box.HEAVY)
        heading_rows = []
        for i in range(len(self._field[0])):
            game.add_column(justify="center", vertical="middle")
            style = "white"
            if i == self._cursor_position:
                style = "red" if not self._player_one_turn else "blue"
            heading_rows.append(Text("  🢃   ", style=style))
        heading = copy.deepcopy(game)
        heading.box = None
        heading.padding = 0
        heading.add_row(*heading_rows)

        for i, row in enumerate(self._field):
            formatted = []
            for j, col in enumerate(row):
                # check if winning coords
                won = False
                if (i, j) in winning_coords:
                    won = True

                if col == "_":
                    formatted.append(Text(" ⬤ ", style="white"))
                elif col == "O":
                    formatted.append(
                        Text(" ⬤ ", style=f"""{"green" if won else "red"}""")
                    )
                elif col == "X":
                    formatted.append(
                        Text(" ⬤ ", style=f"""{"green" if won else "blue"}""")
                    )
            game.add_row(*formatted)

        # capture the ansi tables
        with console.capture() as capture:
            console.print(heading)
        heading_text = "\n".join(capture.get().split("\n")[:-1])
        with console.capture() as capture:
            console.print(game)
        table_text = "\n".join(capture.get().split("\n")[1:-2])

        embed.description = f"""```ansi\n{players_text}\n```\n```ansi\n{heading_text if not winning_coords else ""}\n⁣\n{table_text}\n```"""
        return embed

    def get_components(self, disable: bool = False) -> list[Button]:
        if self.pvp or disable:
            # disable when it's not the players turn
            for component in self._components:
                component.disabled = disable or not self._player_one_turn
        return self._components

    def check_won(self, symbol: Literal["O", "X"]) -> Optional[list[tuple[int, int]]]:
        """Returns a tuple of the indexes that mean the player has won -> (x,y)"""

        # going from top to bot, saving the results in a tuple of 3 (diagonal to left, to bot, diagonal to right) per column
        results: list[list[list[int, int, int]]] = [
            [[0, 0, 0] for _ in range(len(self._field[0]))]
            for _ in range(len(self._field))
        ]
        winning_coords: Optional[list[tuple[int, int]]] = None

        # this is O(N+1), so good enough
        for i, row in enumerate(self._field):
            for j, col in enumerate(row):
                if col == symbol:
                    # left
                    self.__set_value(
                        results=results,
                        i=i,
                        j=j,
                        k=0,
                        new_value=self.__get_value(
                            results=results,
                            i=i - 1,
                            j=j + 1,
                            k=0,
                        )
                        + 1,
                    )

                    # middle
                    self.__set_value(
                        results=results,
                        i=i,
                        j=j,
                        k=1,
                        new_value=self.__get_value(
                            results=results,
                            i=i - 1,
                            j=j,
                            k=1,
                        )
                        + 1,
                    )

                    # right
                    self.__set_value(
                        results=results,
                        i=i,
                        j=j,
                        k=2,
                        new_value=self.__get_value(
                            results=results,
                            i=i - 1,
                            j=j - 1,
                            k=2,
                        )
                        + 1,
                    )

            # check if any winners are found
            try:
                for j, col in enumerate(results[i]):
                    for k, entry in enumerate(col):
                        if entry == self.to_win:
                            # get the winnings coords
                            winning_coords = []
                            for z in range(self.to_win):
                                match k:
                                    case 0:
                                        winning_coords.append((i - z, j + z))
                                    case 1:
                                        winning_coords.append((i - z, j))
                                    case 2:
                                        winning_coords.append((i - z, j - z))
                            raise StopIteration

            except StopIteration:
                break

        return winning_coords

    @staticmethod
    def __get_value(
        results: list[list[list[int, int, int]]], i: int, j: int, k: int
    ) -> int:
        try:
            return results[i][j][k]
        except IndexError:
            return 0

    @staticmethod
    def __set_value(
        results: list[list[list[int, int, int]]], i: int, j: int, k: int, new_value: int
    ):
        try:
            results[i][j][k] = new_value
        except IndexError:
            pass

    async def move_cursor(
        self,
        ctx: ComponentContext,
        move: Literal["left_full", "left_one", "submit", "right_one", "right_full"],
    ):
        max_len = len(self._field[0]) - 1
        match move:
            case "left_full":
                self._cursor_position = 0
            case "left_one":
                self._cursor_position = max(0, self._cursor_position - 1)
            case "right_one":
                self._cursor_position = min(max_len, self._cursor_position + 1)
            case "right_full":
                self._cursor_position = max_len
            case "submit":
                await self.do_turn(ctx=ctx)
                return
        await ctx.edit_origin(embeds=self.get_embed())

    def insert_piece(self, symbol: Literal["O", "X"]) -> bool:
        # check if this col is already full
        if self._field[0][self._cursor_position] != "_":
            return False

        # insert the symbol in the row before the first symbol is found or the last row
        for i, row in enumerate(self._field):
            if row[self._cursor_position] != "_":
                self._field[i - 1][self._cursor_position] = symbol
                return True
        self._field[i][self._cursor_position] = symbol  # noqa
        return True

    async def do_turn(self, ctx: Optional[ComponentContext] = None):
        edit_call = ctx.edit_origin if ctx else self.message.edit

        # play round
        symbol = "X" if self._player_one_turn else "O"
        if ctx:
            if not self.insert_piece(symbol=symbol):  # noqa
                await ctx.send(
                    embeds=embed_message(
                        "Connect 4 Game",
                        f"That row is already full, please choose annother",
                        member=ctx.author,
                    ),
                    ephemeral=True,
                )
                return

        # check winner
        winning_coords = self.check_won(symbol=symbol)  # noqa

        # flip whose turn it is before sending embed
        self._player_one_turn = not self._player_one_turn
        await edit_call(
            embeds=self.get_embed(winning_coords=winning_coords),
            components=self.get_components(disable=bool(winning_coords)),
        )

        if winning_coords:
            _games.pop(ctx.author.id)
        else:
            # next computer turn
            if self.pvp and not self._player_one_turn:
                await self.computer_turn(symbol="O")

    async def computer_turn(self, symbol: Literal["O", "X"]):
        # todo computer logic
        return
        await self.do_turn()
