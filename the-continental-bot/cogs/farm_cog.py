import discord
from discord.ext import commands
from discord import app_commands

from views.farmview import FarmView, enviar_botao_se_necessario
from utils.utils_embeds import criar_embed


class FarmCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="farm", description="Força o envio do botão de farm no canal atual")
    async def farm(self, interaction: discord.Interaction):
        canal = interaction.channel
        async for msg in canal.history(limit=50):
            if msg.author == self.bot.user and msg.components:
                try:
                    await msg.delete()
                except Exception:
                    pass
        await enviar_botao_se_necessario(canal, self.bot.user)
        await interaction.response.send_message("✅ Botão de farm recriado!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(FarmCog(bot))