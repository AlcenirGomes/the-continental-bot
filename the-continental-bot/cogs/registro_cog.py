import discord
from discord.ext import commands
import logging

# Importação da função utilitária, removendo a duplicação
from ..utils.utils_discord import limpar_e_enviar_view

logger = logging.getLogger(__name__)

class RegistroCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

async def setup(bot: commands.Bot):
    await bot.add_cog(RegistroCog(bot))