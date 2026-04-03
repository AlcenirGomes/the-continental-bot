import discord
from discord.ext import commands
from discord import app_commands

from config import CANAL_REGISTRO_ID, ID_MARCADOR_REGISTRO
from views.registro import RegistroView
from utils.utils_embeds import criar_embed


class RegistrarCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='registrar', description='Forca o envio do botao de registro no canal de registro')
    async def registrar(self, interaction: discord.Interaction):
        canal = self.bot.get_channel(CANAL_REGISTRO_ID)
        if not canal:
            await interaction.response.send_message('Canal de registro nao encontrado.', ephemeral=True)
            return
        async for msg in canal.history(limit=50):
            if msg.author == self.bot.user and msg.components:
                try:
                    await msg.delete()
                except discord.HTTPException:
                    pass
        await canal.send(content=ID_MARCADOR_REGISTRO, embed=criar_embed(title='Registro de Novos Membros', description='Clique no botao abaixo para registrar-se no cartel.', color=0x272727), view=RegistroView())
        await interaction.response.send_message('Botao de registro recriado!', ephemeral=True)


async def setup(bot):
    await bot.add_cog(RegistrarCog(bot))