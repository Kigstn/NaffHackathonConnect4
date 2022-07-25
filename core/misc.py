from typing import Optional

from naff import Colour, Embed, Guild, Member, User


def embed_message(
    title: Optional[str] = None,
    description: Optional[str] = None,
    footer: Optional[str] = None,
    member: Optional[Member | User] = None,
    guild: Optional[Guild] = None,
) -> Embed:
    """Takes title description and footer and returns an Embed"""

    assert (
        title is not None or description is not None or footer is not None
    ), "Need to input either title or description or footer"

    if not member or guild:
        embed = Embed(title=title, description=description, color=Colour.from_hex("#71b093"))
    else:
        embed = Embed(description=description, color=Colour.from_hex("#71b093"))
        if member:
            if isinstance(member, Member):
                embed.set_author(name=f"{member.display_name}'s {title}", icon_url=member.display_avatar.url)
            else:
                embed.set_author(name=f"{member.username}#{member.discriminator}'s {title}", icon_url=member.avatar.url)
        elif guild:
            embed.set_author(name=f"{guild.name}'s {title}", icon_url=guild.icon.url)

    if footer:
        embed.set_footer(text=footer)
    return embed
