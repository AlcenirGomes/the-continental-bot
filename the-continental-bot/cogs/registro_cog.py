import discord
from discord.ext import commands
import logging

# CORRIGIDO: Importação da função utilitária, removendo a duplicação
from ..utils.utils_discord import limpar_e_enviar_view

logger = logging.getLogger(__name__)

# A função limpar_e_enviar_view foi removida daqui para evitar duplicação.
# Ela agora é importada de ..utils.utils_discord.

class RegistroCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Você pode adicionar comandos de barra ou de prefixo relacionados a registro aqui, se necessário.
    # Por exemplo, um comando para forçar a recriação do botão de registro.

async def setup(bot: commands.Bot):
    await bot.add_cog(RegistroCog(bot))