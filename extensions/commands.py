from core.base import CustomClient

from naff import (
    Button,
    ButtonStyles,
    ComponentContext,
    Embed,
    Extension,
    InteractionContext,
    OptionTypes,
    SlashCommandChoice,
    component_callback,
    slash_command,
    slash_option,
)

from core.connect_4 import Connect4, GameExists
from core.misc import embed_message


# todo delete game command


class CommandExtension(Extension):
    bot: CustomClient

    @slash_command(
        name="connect4",
        description="Play Connect 4",
        sub_cmd_name="computer",
        sub_cmd_description="Play vs computer",
    )
    @slash_option(
        name="difficulty",
        description="How good the computer should play. Default: `Normal`",
        opt_type=OptionTypes.INTEGER,
        required=False,
        choices=[
            SlashCommandChoice(name="Very Easy", value=0),
            SlashCommandChoice(name="Easy", value=1),
            SlashCommandChoice(name="Normal", value=2),
            SlashCommandChoice(name="Hard", value=3),
            SlashCommandChoice(name="Very Hard", value=5),
            SlashCommandChoice(name="Impossible", value=7),
        ],
    )
    async def computer(self, ctx: InteractionContext, difficulty: int = 2):
        try:
            game = Connect4(ctx=ctx, pvp=True, pvp_difficulty=difficulty)
        except GameExists as e:
            await ctx.send(
                embeds=embed_message(
                    "Connect 4 Game",
                    "You already have a game in progress, please finish that first.",
                    member=ctx.author,
                ),
                ephemeral=True,
                components=Button(
                    style=ButtonStyles.URL,
                    label="Go To Game",
                    url=e.game.message.jump_url,
                ),
            )
        else:
            await game.play()


def setup(bot: CustomClient):
    """Let naff load the extension"""

    CommandExtension(bot)
