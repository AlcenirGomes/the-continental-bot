import discord
from discord.ext import commands
from discord import app_commands

from config import ID_MARCADOR
from views.farmview import FarmView
from utils.utils_embeds import criar_embed


class FarmCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='farm', description='Forca o envio do botao de farm no canal atual')
    async def farm(self, interaction: discord.Interaction):
        canal = interaction.channel
        async for msg in canal.history(limit=50):
            if msg.author == self.bot.user and msg.components:
                try:
                    await msg.delete()
                except discord.HTTPException:
                    pass
        await canal.send(content=ID_MARCADOR, embed=criar_embed(title='Entrega do Farm Semanal', description='Clique no botao abaixo para entregar seu farm.', color=0x272727), view=FarmView())
        await interaction.response.send_message('Botao de farm recriado no canal atual!', ephemeral=True)


async def setup(bot):
    await bot.add_cog(FarmCog(bot))