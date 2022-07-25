from core.base import CustomClient

from naff import (
    Button,
    ButtonStyles,
    ComponentContext,
    Embed,
    Extension,
    InteractionContext,
    component_callback,
    slash_command,
)

from core.connect_4 import Connect4, GameExists
from core.misc import embed_message


# todo delete game command


class CommandExtension(Extension):
    bot: CustomClient

    @slash_command(name="connect4", description="Play Connect 4")
    async def connect_4(self, ctx: InteractionContext):
        try:
            game = Connect4(ctx=ctx, pvp=True)
        except GameExists as e:
            await ctx.send(
                embeds=embed_message(
                    "Connect 4 Game",
                    "You already have a game in progress, please finish that first.",
                    member=ctx.author
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


        # # adds a component to the message
        # components = Button(
        #     style=ButtonStyles.GREEN, label="Hiya", custom_id="hello_world_button"
        # )
        #
        # # adds an embed to the message
        # embed = Embed(title="Hello World 2", description="Now extra fancy")
        #
        # # respond to the interaction
        # await ctx.send("Hello World", embeds=embed, components=components)

    @component_callback("hello_world_button")
    async def my_callback(self, ctx: ComponentContext):
        """Callback for the component from the hello_world command"""

        await ctx.send("Hiya to you too")


def setup(bot: CustomClient):
    """Let naff load the extension"""

    CommandExtension(bot)
