import discord
from discord.ext import commands
from discord import app_commands

from registro import RegistroView
from utils_embeds import criar_embed
from config import CANAL_REGISTRO_ID, ID_MARCADOR_REGISTRO # Adicionado ID_MARCADOR_REGISTRO

class RegistrarCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="registrar", description="Força o envio do botão de registro no canal de registro")
    async def registrar(self, interaction: discord.Interaction):
        canal = self.bot.get_channel(CANAL_REGISTRO_ID)
        if not canal:
            await interaction.response.send_message("❌ Canal de registro não encontrado.", ephemeral=True)
            return

        async for msg in canal.history(limit=50):
            if msg.author == self.bot.user and msg.components:
                try:
                    await msg.delete()
                except Exception:
                    pass

        await canal.send(
            content=ID_MARCADOR_REGISTRO, # Usar ID_MARCADOR_REGISTRO
            embed=criar_embed(
                title="📋 Registro de Novos Membros",
                description="Clique no botão abaixo para registrar-se no cartel.",
                color=0x272727,
            ),
            view=RegistroView()
        )

        await interaction.response.send_message("✅ Botão de registro recriado no canal de registro!", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(RegistrarCog(bot))