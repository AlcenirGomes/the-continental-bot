import discord
from discord.ext import commands
from discord import app_commands
import logging

from ..views.farmview import FarmView # Importação relativa corrigida
from ..utils.utils_embeds import criar_embed # Importação relativa corrigida
from ..utils.utils_discord import limpar_e_enviar_view # Importação da nova função utilitária
from ..config import ID_MARCADOR, CATEGORIA_FARM_ID # Importação relativa corrigida

logger = logging.getLogger(__name__)

class FarmCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="farm", description="Força o envio do botão de farm no canal atual")
    async def farm(self, interaction: discord.Interaction):
        canal = interaction.channel
        if canal.category_id != CATEGORIA_FARM_ID:
            await interaction.response.send_message("❌ Este comando só pode ser usado em canais de farm.", ephemeral=True)
            logger.warning(f"Comando /farm: Tentativa de uso em canal não-farm por {interaction.user.display_name}.")
            return

        embed = criar_embed(
            title="Entrega do Farm Semanal",
            description="Clique no botão abaixo para entregar seu farm.",
            color=0x272727
        )
        view = FarmView()

        await limpar_e_enviar_view(
            canal,
            self.bot.user,
            ID_MARCADOR,
            embed,
            view,
            getattr(self.bot, "_suppress_recreate_farm", set()),
            canal.id
        )
        await interaction.response.send_message("✅ Botão de farm recriado!", ephemeral=True)
        logger.info(f"Comando /farm: Botão de farm recriado por {interaction.user.display_name} no canal {canal.name}.")

async def setup(bot):
    await bot.add_cog(FarmCog(bot))