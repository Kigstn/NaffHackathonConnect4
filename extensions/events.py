from naff.api.events import Component

from core.base import CustomClient

from naff import listen, Extension

from core.connect_4 import Connect4
from core.misc import embed_message


class EventExtension(Extension):
    bot: CustomClient

    @listen()
    async def on_component(self, event: Component):
        author_id, move = event.context.custom_id.split("|")

        game = Connect4.get_existing(author_id=int(author_id))
        if not game:
            await event.context.send(
                embeds=embed_message(
                    "Connect 4 Game",
                    f"My power went out so I lost all info about this game\nSorry, gotta restart by using `/connect4`",
                    member=event.context.author
                ),
                ephemeral=True,
            )
        else:
            async with game.lock:
                await game.move_cursor(ctx=event.context, move=move)




def setup(bot: CustomClient):
    """Let naff load the extension"""

    EventExtension(bot)
