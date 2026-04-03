import discord
from discord.ui import Button, View
import logging

from ..config import (
    CARGOS_AUTORIZADOS,
    CATEGORIA_FARM_ID,
    ID_MARCADOR,
)
from ..utils.utils_embeds import criar_embed
from ..utils.utils_discord import limpar_e_enviar_view
# from .farmview import FarmView # FarmView é importada dentro de finalizar_coleta para evitar importação circular

logger = logging.getLogger(__name__)

class AvaliacaoView(View):
    def __init__(self, mensagem_embed: discord.Message, embed_original: discord.Embed, user: discord.User):
        super().__init__(timeout=None)
        self.mensagem_embed = mensagem_embed
        self.embed_original = embed_original
        self.user = user

    async def verificar_permissao(self, interaction: discord.Interaction) -> bool:
        cargos_usuario = {r.name.lower() for r in interaction.user.roles} # CORRIGIDO: Usa set para comparação
        if not (cargos_usuario & set(CARGOS_AUTORIZADOS)): # CORRIGIDO: Compara com CARGOS_AUTORIZADOS
            await interaction.response.send_message(
                "❌ Você não tem permissão para aprovar ou recusar coletas.",
                ephemeral=True
            )
            logger.warning(f"Tentativa de aprovação/reprovação de coleta sem permissão por {interaction.user.display_name}.")
            return False
        return True

    @discord.ui.button(label="✔️ Aprovar", style=discord.ButtonStyle.success, custom_id="aprovar_coleta")
    async def aprovar(self, interaction: discord.Interaction, button: Button):
        if not await self.verificar_permissao(interaction):
            return
        await self.finalizar_coleta(interaction, aprovado=True)

    @discord.ui.button(label="❌ Reprovar", style=discord.ButtonStyle.danger, custom_id="reprovar_coleta")
    async def reprovar(self, interaction: discord.Interaction, button: Button):
        if not await self.verificar_permissao(interaction):
            return
        await self.finalizar_coleta(interaction, aprovado=False)

    async def finalizar_coleta(self, interaction: discord.Interaction, aprovado: bool):
        bot = interaction.client
        if not hasattr(bot, "_suppress_recreate_farm"):
            bot._suppress_recreate_farm = set()

        try:
            titulo = "📦 Coleta Aprovada" if aprovado else "📦 Coleta Reprovada"
            descricao = (
                f"{self.user.mention} sua coleta foi **aprovada** ✅"
                if aprovado else
                f"{self.user.mention} sua coleta foi **reprovada** ❌"
            )

            embed_status = criar_embed(
                title=titulo,
                description=descricao,
                color=0x2ecc71 if aprovado else 0xe74c3c,
                footer_text=f"Avaliado por {interaction.user.display_name}",
            )

            try:
                await self.mensagem_embed.edit(view=None)
            except Exception:
                logger.warning("Não foi possível editar a mensagem original da coleta para remover a view.")
                pass

            await interaction.channel.send(embed=embed_status)
            logger.info(f"Coleta de {self.user.display_name} {titulo.lower().replace('📦 ', '')} por {interaction.user.display_name}.")

            if interaction.channel.category_id == CATEGORIA_FARM_ID:
                from .farmview import FarmView # Importar FarmView aqui para evitar importação circular
                embed_farm = criar_embed(
                    title="Entrega do Farm Semanal",
                    description="Clique no botão abaixo para entregar seu farm.",
                    color=0x272727,
                )
                await limpar_e_enviar_view(
                    interaction.channel,
                    bot.user,
                    ID_MARCADOR,
                    embed_farm,
                    FarmView(),
                    bot._suppress_recreate_farm,
                    interaction.channel.id
                )

            await interaction.response.send_message("✅ Avaliação registrada.", ephemeral=True)

        except Exception as e:
            logger.error(f"Erro ao finalizar avaliação de coleta: {e}", exc_info=True)
            await interaction.response.send_message(
                f"❌ Erro ao finalizar avaliação: {str(e)}", ephemeral=True
            )