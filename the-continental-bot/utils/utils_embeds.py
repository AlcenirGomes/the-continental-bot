import discord

LOGO_URL = "https://cdn.discordapp.com/attachments/1398335026122457101/1411607646003527762/The_Continental_Logo.png?ex=68b54591&is=68b3f411&hm=bf0eecc941e85d25e5f182fcde1d6e750d2330c1352213c3131bfb0eac4efcc7&"
FOOTER_PREFIX = "Alta Cúpula The Continental!!!"

def criar_embed(
    title: str | None = None,
    description: str | None = None,
    color: discord.Color | int = 0x272727,
    footer_text: str = "",
    image_url: str | None = None,
) -> discord.Embed:
    if isinstance(color, int):
        color = discord.Color(color)

    embed = discord.Embed(title=title, description=description, color=color)

    texto_footer = FOOTER_PREFIX if not footer_text else f"{FOOTER_PREFIX} | {footer_text}"
    embed.set_footer(text=texto_footer, icon_url=LOGO_URL or None) # CORRIGIDO: Usar 'or None'

    if LOGO_URL:
        embed.set_thumbnail(url=LOGO_URL)

    if image_url:
        embed.set_image(url=image_url)

    return embed