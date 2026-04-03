import discord
from discord.ui import Button, View

from config import (
    CARGOS_AUTORIZADOS,
    CATEGORIA_FARM_ID,
    ID_MARCADOR,
)
from farmview import FarmView
from utils_embeds import criar_embed

class AvaliacaoView(View):
    def __init__(self, mensagem_embed, embed_original, user):
        super().__init__(timeout=None)
        self.mensagem_embed = mensagem_embed
        self.embed_original = embed_original
        self.user = user

    async def verificar_permissao(self, interaction: discord.Interaction) -> bool:
        cargos = [r.name.lower() for r in interaction.user.roles]
        if not any(cargo in CARGOS_AUTORIZADOS for cargo in cargos):
            await interaction.response.send_message(
                "❌ Você não tem permissão para aprovar ou recusar coletas.",
                ephemeral=True
            )
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

        bot._suppress_recreate_farm.add(interaction.channel.id)

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
                pass

            await interaction.channel.send(embed=embed_status)

            async for msg in interaction.channel.history(limit=50):
                if msg.author == bot.user and msg.components:
                    try:
                        await msg.delete()
                    except Exception:
                        pass

            if interaction.channel.category_id == CATEGORIA_FARM_ID:
                await interaction.channel.send(
                    content=ID_MARCADOR,
                    embed=criar_embed(
                        title="Entrega do Farm Semanal",
                        description="Clique no botão abaixo para entregar seu farm.",
                        color=0x272727,
                    ),
                    view=FarmView()
                )

            await interaction.response.send_message("✅ Avaliação registrada.", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(
                f"❌ Erro ao finalizar avaliação: {str(e)}", ephemeral=True
            )
        finally:
            try:
                bot._suppress_recreate_farm.discard(interaction.channel.id)
            except Exception:
                pass