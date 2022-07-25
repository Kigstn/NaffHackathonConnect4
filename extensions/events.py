from core.base import CustomClient

from naff import ComponentContext, listen, Extension

from core.connect_4 import Connect4
from core.misc import embed_message


class EventExtension(Extension):
    bot: CustomClient

    @listen()
    async def on_component(self, ctx: ComponentContext):
        author_id, move = ctx.custom_id.split("|")

        game = Connect4.get_existing(author_id=author_id)
        if not game:
            await ctx.send(
                embeds=embed_message(
                    "Connect 4 Game",
                    f"My power went out so I lost all info about this game\nSorry, gotta restart by using `/connect4`",
                    member=ctx.author
                ),
                ephemeral=True,
            )
        else:
            async with game.lock:
                await game.move_cursor(ctx=ctx, move=move)




def setup(bot: CustomClient):
    """Let naff load the extension"""

    EventExtension(bot)
