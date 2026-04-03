import discord
from discord.ext import commands
from discord import app_commands
import logging

from ..views.farmview import FarmView
from ..utils.utils_embeds import criar_embed
from ..utils.utils_discord import limpar_e_enviar_view
from ..config import ID_MARCADOR, CATEGORIA_FARM_ID

logger = logging.getLogger(__name__)

class FarmCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="farm", description="Força o envio do botão de farm no canal atual")
    async def farm(self, interaction: discord.Interaction):
        canal = interaction.channel
        # CORRIGIDO: Verifica se é TextChannel antes de acessar .category_id
        if not isinstance(canal, discord.TextChannel) or canal.category_id != CATEGORIA_FARM_ID:
            await interaction.response.send_message("❌ Este comando só pode ser usado em canais de farm.", ephemeral=True)
            logger.warning(f"Comando /farm: Tentativa de uso em canal não-farm por {interaction.user.display_name}.")
            return

        embed = criar_embed(
            title="Entrega do Farm Semanal",
            description="Clique no botão abaixo para entregar seu farm.",
            color=0x272727
        )
        view = FarmView()

        try:
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
        except discord.Forbidden:
            await interaction.response.send_message("❌ Não tenho permissão para enviar mensagens ou deletar em neste canal.", ephemeral=True)
            logger.warning(f"Comando /farm: Sem permissão para operar em {canal.name} (ID: {canal.id}).")
        except Exception as e:
            logger.error(f"Comando /farm: Erro ao recriar botão de farm em {canal.name} (ID: {canal.id}): {e}", exc_info=True)
            await interaction.response.send_message("❌ Ocorreu um erro ao recriar o botão de farm.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(FarmCog(bot))