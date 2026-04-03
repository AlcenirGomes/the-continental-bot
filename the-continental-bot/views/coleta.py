import discord
import logging
from discord.ui import Button, View

from config import CARGOS_AUTORIZADOS, CATEGORIA_FARM_ID, ID_MARCADOR
from utils.utils_embeds import criar_embed

logger = logging.getLogger(__name__)


class AvaliacaoView(View):
    def __init__(self, mensagem_embed, embed_original, user):
        super().__init__(timeout=None)
        self.mensagem_embed  = mensagem_embed
        self.embed_original  = embed_original
        self.user            = user

    async def verificar_permissao(self, interaction: discord.Interaction):
        cargos = [r.name.lower() for r in interaction.user.roles]
        if not any(cargo in CARGOS_AUTORIZADOS for cargo in cargos):
            await interaction.response.send_message('Voce nao tem permissao para aprovar ou recusar coletas.', ephemeral=True)
            return False
        return True

    @discord.ui.button(label='Aprovar',  style=discord.ButtonStyle.success, custom_id='aprovar_coleta')
    async def aprovar(self, interaction: discord.Interaction, button: Button):
        if not await self.verificar_permissao(interaction):
            return
        await self.finalizar_coleta(interaction, aprovado=True)

    @discord.ui.button(label='Reprovar', style=discord.ButtonStyle.danger,  custom_id='reprovar_coleta')
    async def reprovar(self, interaction: discord.Interaction, button: Button):
        if not await self.verificar_permissao(interaction):
            return
        await self.finalizar_coleta(interaction, aprovado=False)

    async def finalizar_coleta(self, interaction: discord.Interaction, aprovado: bool):
        from views.farmview import FarmView
        bot = interaction.client
        if not hasattr(bot, '_suppress_recreate_farm'):
            bot._suppress_recreate_farm = set()
        bot._suppress_recreate_farm.add(interaction.channel.id)
        try:
            await interaction.response.defer(ephemeral=True)
            titulo    = 'Coleta Aprovada'   if aprovado else 'Coleta Reprovada'
            descricao = (f'{self.user.mention} sua coleta foi aprovada' if aprovado else f'{self.user.mention} sua coleta foi reprovada')
            embed_status = criar_embed(title=titulo, description=descricao, color=0x2ecc71 if aprovado else 0xe74c3c, footer_text=f'Avaliado por {interaction.user.display_name}')
            try:
                await self.mensagem_embed.edit(view=None)
            except discord.HTTPException:
                pass
            await interaction.channel.send(embed=embed_status)
            if interaction.channel.category_id == CATEGORIA_FARM_ID:
                async for msg in interaction.channel.history(limit=50):
                    if msg.author == bot.user and msg.components:
                        try:
                            await msg.delete()
                        except discord.HTTPException:
                            pass
                await interaction.channel.send(content=ID_MARCADOR, embed=criar_embed(title='Entrega do Farm Semanal', description='Clique no botao abaixo para entregar seu farm.', color=0x272727), view=FarmView())
            await interaction.followup.send('Avaliacao registrada.', ephemeral=True)
        except Exception:
            logger.exception('Erro ao finalizar avaliacao de coleta')
            try:
                await interaction.followup.send('Erro ao finalizar avaliacao.', ephemeral=True)
            except discord.HTTPException:
                pass
        finally:
            bot._suppress_recreate_farm.discard(interaction.channel.id)