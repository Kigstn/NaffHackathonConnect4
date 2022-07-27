import asyncio
import copy
import logging
import math
import random
from typing import Literal, Optional

import attrs
from anyio import to_thread
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
    pvp_difficulty: int = attrs.field(default=0)
    to_win: int = attrs.field(default=4)

    message: Message = attrs.field(init=False)
    logger = attrs.field(init=False, default=logging.getLogger("Connect4"))
    lock = attrs.field(init=False, default=asyncio.Lock())

    _field: list[list[Literal["_", "O", "X"]]] = attrs.field(init=False)
    _components: list[Button] = attrs.field(init=False)
    _player_one_turn: bool = attrs.field(
        init=False, default=random.choice([True, False])
    )
    _player_one: Member = attrs.field(init=False)
    _player_two: Optional[Member] = attrs.field(init=False, default=None)
    _player_one_cursor: int = attrs.field(init=False)
    _player_two_cursor: int = attrs.field(init=False)
    _pvp_chance_to_fail: float = attrs.field(init=False)

    def __init__(self, ctx: InteractionContext, *args, **kwargs):
        # do not allow multiple games
        if game := _games.get(ctx.author.id):
            raise GameExists(game)
        self.__attrs_init__(ctx, *args, **kwargs)

    def __attrs_post_init__(self):
        self._player_one = self.ctx.author

        match self.pvp_difficulty:
            case 1:
                self._pvp_chance_to_fail = 0.2
            case 2:
                self._pvp_chance_to_fail = 0.15
            case 3:
                self._pvp_chance_to_fail = 0.1
            case _:
                self._pvp_chance_to_fail = 0

        self._field = [
            ["_", "_", "_", "_", "_", "_", "_"],
            ["_", "_", "_", "_", "_", "_", "_"],
            ["_", "_", "_", "_", "_", "_", "_"],
            ["_", "_", "_", "_", "_", "_", "_"],
            ["_", "_", "_", "_", "_", "_", "_"],
            ["_", "_", "_", "_", "_", "_", "_"],
        ]
        self._components = [
            Button(
                custom_id=f"{self.ctx.author.id}|left_full",
                style=ButtonStyles.BLUE,
                label="«",
            ),
            Button(
                custom_id=f"{self.ctx.author.id}|left_one",
                style=ButtonStyles.RED,
                label="‹",
            ),
            Button(
                custom_id=f"{self.ctx.author.id}|submit",
                style=ButtonStyles.GREEN,
                label="🢃",
            ),
            Button(
                custom_id=f"{self.ctx.author.id}|right_one",
                style=ButtonStyles.RED,
                label="›",
            ),
            Button(
                custom_id=f"{self.ctx.author.id}|right_full",
                style=ButtonStyles.BLUE,
                label="»",
            ),
        ]

        self._player_one_cursor = int(len(self._field[0]) / 2)
        self._player_two_cursor = self._player_one_cursor

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
            await self.computer_turn()

    def get_embed(
        self,
        winning_coords: Optional[list[tuple[int, int]]] = None,
        game_over: bool = False,
    ) -> Embed:
        if winning_coords is None:
            winning_coords = []

        if self._player_one_turn:
            if not winning_coords:
                footer = f"{self._player_one.display_name}'s turn"
            elif self.pvp:
                footer = "Computer won!"
            else:
                footer = f"{self._player_two.display_name} won!"
        elif self.pvp:
            footer = (
                "Computer is thinking..."
                if not winning_coords
                else f"{self._player_one.display_name} won!"
            )
        elif self._player_two:
            footer = (
                f"{self._player_two.display_name}'s turn"
                if not winning_coords
                else f"{self._player_one.display_name} won!"
            )
        else:
            footer = "Waiting for player..."

        embed = embed_message(
            "Connect 4 Game",
            footer=footer if not game_over else "Game Over! Nobody won",
            member=self.ctx.author,
        )

        # which player is what
        console = Console()
        players = Text.assemble(
            ("● ", "white"),
            " - Free\n",
            ("●", "blue"),
            ("●", "green") if winning_coords and not self._player_one_turn else " ",
            f" - {self.ctx.author.display_name}\n",
            ("●", "red"),
            ("●", "green") if winning_coords and self._player_one_turn else " ",
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
            if self._player_one_turn:
                if i == self._player_one_cursor:
                    style = "blue"
            elif not self.pvp:
                if i == self._player_two_cursor:
                    style = "red"
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
        heading_text = "\n".join(capture.get().split("\n"))
        heading_text += "⁣"
        with console.capture() as capture:
            console.print(game)
        table_text = "\n".join(capture.get().split("\n")[1:-2])

        embed.description = f"""```ansi\n{players_text}\n```\n```ansi\n{heading_text if not winning_coords and not game_over else ""}\n{table_text}\n```"""
        return embed

    def get_components(self) -> list[Button]:
        if self.pvp:
            # disable when it's not the players turn
            for component in self._components:
                component.disabled = not self._player_one_turn
        return self._components

    def check_won(
        self,
        symbol: Literal["O", "X"],
        field: Optional[list[list[Literal["_", "O", "X"]]]] = None,
    ) -> Optional[list[tuple[int, int]]]:
        """Returns a tuple of the indexes that mean the player has won -> (x,y)"""

        if not field:
            field = self._field

        # going from top to bot, saving the results in a tuple of 3 (diagonal to left, to bot, diagonal to right, same row left) per column
        results: list[list[list[int, int, int, int]]] = [
            [[0, 0, 0, 0] for _ in range(len(field[0]))] for _ in range(len(field))
        ]
        winning_coords: Optional[list[tuple[int, int]]] = None

        # this is O(N+1), so good enough
        for i, row in enumerate(field):
            for j, col in enumerate(row):
                if col == symbol:
                    # left
                    k = 0
                    self.__set_value(
                        results=results,
                        i=i,
                        j=j,
                        k=k,
                        new_value=self.__get_value(
                            results=results,
                            i=i - 1,
                            j=j + 1,
                            k=k,
                        )
                        + 1,
                    )

                    # middle
                    k = 1
                    self.__set_value(
                        results=results,
                        i=i,
                        j=j,
                        k=k,
                        new_value=self.__get_value(
                            results=results,
                            i=i - 1,
                            j=j,
                            k=k,
                        )
                        + 1,
                    )

                    # right
                    k = 2
                    self.__set_value(
                        results=results,
                        i=i,
                        j=j,
                        k=k,
                        new_value=self.__get_value(
                            results=results,
                            i=i - 1,
                            j=j - 1,
                            k=k,
                        )
                        + 1,
                    )

                    # same row
                    k = 3
                    self.__set_value(
                        results=results,
                        i=i,
                        j=j,
                        k=k,
                        new_value=self.__get_value(
                            results=results,
                            i=i,
                            j=j - 1,
                            k=k,
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
                                    case 3:
                                        winning_coords.append((i, j - z))
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
        # correct player?
        if self._player_one_turn:
            if ctx.author != self._player_one:
                await ctx.send(
                    embeds=embed_message(
                        "Connect 4 Game",
                        f"**Not your turn!**\nIt's {self._player_one.mention}'s turn",
                        member=self.ctx.author,
                    ),
                    ephemeral=True,
                )
                return
        else:
            if self.pvp:
                return
            if not self._player_two:
                if ctx.author == self._player_one:
                    await ctx.send(
                        embeds=embed_message(
                            "Connect 4 Game",
                            f"You cannot play vs yourself.",
                            member=self.ctx.author,
                        ),
                        ephemeral=True,
                    )
                    return
                self._player_two = ctx.author
            else:
                if self._player_two != ctx.author:
                    await ctx.send(
                        embeds=embed_message(
                            "Connect 4 Game",
                            f"**Not your turn!**\nIt's {self._player_two.mention}'s turn",
                            member=self.ctx.author,
                        ),
                        ephemeral=True,
                    )
                    return

        if self._player_one_turn:
            position = self._player_one_cursor
        else:
            position = self._player_two_cursor

        max_len = len(self._field[0]) - 1
        match move:
            case "left_full":
                position = 0
            case "left_one":
                position = max(0, position - 1)
            case "right_one":
                position = min(max_len, position + 1)
            case "right_full":
                position = max_len
            case "submit":
                await self.do_turn(ctx=ctx, position=position)
                return

        if self._player_one_turn:
            self._player_one_cursor = position
        else:
            self._player_two_cursor = position
        await ctx.edit_origin(embeds=self.get_embed())

    def insert_piece(
        self,
        symbol: Literal["O", "X"],
        position: int,
        field: Optional[list[list[Literal["_", "O", "X"]]]] = None,
    ) -> Optional[list[list[Literal["_", "O", "X"]]]]:
        if not field:
            field = self._field

        # check if this col is already full
        if field[0][position] != "_":
            return None

        # insert the symbol in the row before the first symbol is found or the last row
        for i, row in enumerate(field):
            if row[position] != "_":
                field[i - 1][position] = symbol  # noqa
                return field
        field[i][position] = symbol  # noqa
        return field

    async def do_turn(self, position: int, ctx: Optional[ComponentContext] = None):
        edit_call = ctx.edit_origin if ctx else self.message.edit
        symbol = "X" if self._player_one_turn else "O"

        # play round
        if not self.insert_piece(symbol=symbol, position=position):  # noqa
            if ctx:
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
        game_over = self.check_game_over(winning_coords)

        # flip whose turn it is before sending embed
        self._player_one_turn = not self._player_one_turn
        await edit_call(
            embeds=self.get_embed(winning_coords=winning_coords, game_over=game_over),
            components=[]
            if bool(winning_coords) or game_over
            else self.get_components(),
        )

        if winning_coords or game_over:
            _games.pop(self.ctx.author.id)
        else:
            # next computer turn
            if self.pvp and not self._player_one_turn:
                await self.computer_turn()

    def check_game_over(
        self,
        winning_coords: Optional[list[tuple[int, int]]] = None,
        field: Optional[list[list[Literal["_", "O", "X"]]]] = None,
    ) -> bool:
        if not field:
            field = self._field

        if winning_coords:
            return False
        elif not self._get_valid_moves(field):
            return True
        return False

    def _get_valid_moves(
        self, field: Optional[list[list[Literal["_", "O", "X"]]]] = None
    ) -> list[int]:
        if not field:
            field = self._field

        valid = []
        for i, col in enumerate(field[0]):
            if col == "_":
                valid.append(i)
        return valid

    async def computer_turn(self):
        best_position = await to_thread.run_sync(lambda: self._computer_minimax())

        await self.do_turn(position=best_position)

    def get_winner_symbol(
        self, field: Optional[list[list[Literal["_", "O", "X"]]]] = None
    ) -> Optional[Literal["O", "X"]]:
        if not field:
            field = self._field

        if self.check_won("O", field=field):
            return "O"
        elif self.check_won("X", field=field):
            return "X"
        return None

    def _computer_minimax(self) -> int:
        best_move, score = self.__computer_minimax(
            is_maximizing=True,
            depth=self.pvp_difficulty,
            field=copy.deepcopy(self._field),
        )
        # rarely ignore the minimax suggestions
        if best_move and random.random() > self._pvp_chance_to_fail:
            return best_move
        else:
            return random.choice(self._get_valid_moves())

    # todo give it a chance no to see a win
    def __computer_minimax(
        self,
        is_maximizing: bool,
        depth: int,
        field: list[list[Literal["_", "O", "X"]]],
        alpha: int = -math.inf,
        beta: int = math.inf,
    ) -> tuple[Optional[int], int]:
        # anyone won?
        # game over?
        # max depth reached?
        winner = self.get_winner_symbol(field)
        valid_moves = self._get_valid_moves(field)
        if depth == 0 or winner or not valid_moves:
            if winner == "O":
                return None, 1
            elif winner == "X":
                return None, -1
            else:
                return None, 0
            # match winner:
            #     case "O":
            #         return None, 1
            #     case "X":
            #         return None, -1
            #     case None:
            #         return None, 0

        # max scores for each option
        if is_maximizing:
            best_score = -math.inf
            symbol = "O"
        else:
            best_score = math.inf
            symbol = "X"

        # check each possible play
        best_move = None
        for cursor_position in valid_moves:
            field_copy = copy.deepcopy(field)
            self.insert_piece(
                symbol=symbol, position=cursor_position, field=field_copy
            )  # noqa
            _, minimax_score = self.__computer_minimax(
                is_maximizing=not is_maximizing,
                field=field_copy,
                depth=depth - 1,
                alpha=alpha,
                beta=beta,
            )

            # alpha beta pruning -> https://en.wikipedia.org/wiki/Alpha%E2%80%93beta_pruning
            if is_maximizing:
                if minimax_score > best_score:
                    best_score = minimax_score
                    best_move = cursor_position
                if best_score >= beta:
                    break
                alpha = max(alpha, best_score)
            else:
                if minimax_score < best_score:
                    best_score = minimax_score
                    best_move = cursor_position
                if best_score <= alpha:
                    break
                beta = min(beta, best_score)

        return best_move, best_score
