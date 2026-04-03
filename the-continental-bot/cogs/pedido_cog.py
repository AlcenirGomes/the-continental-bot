import discord
from discord.ext import commands
from discord import app_commands

from pedido import PedidoView
from utils_embeds import criar_embed
from config import CANAL_PEDIDO_ID, ID_MARCADOR_PEDIDO # Adicionado ID_MARCADOR_PEDIDO

class PedidoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="pedido", description="Força o envio do botão de pedidos no canal de pedidos")
    async def pedido(self, interaction: discord.Interaction):
        canal = self.bot.get_channel(CANAL_PEDIDO_ID)
        if not canal:
            await interaction.response.send_message("❌ Canal de pedidos não encontrado.", ephemeral=True)
            return

        async for msg in canal.history(limit=50):
            if msg.author == self.bot.user and msg.components:
                try:
                    await msg.delete()
                except Exception:
                    pass

        await canal.send(
            content=ID_MARCADOR_PEDIDO, # Usar ID_MARCADOR_PEDIDO
            embed=criar_embed(
                title="📦 Pedidos de Armas",
                description="Clique no botão abaixo para solicitar um orçamento.",
                color=0x272727,
            ),
            view=PedidoView(self.bot)
        )

        await interaction.response.send_message("✅ Botão de pedidos recriado no canal de pedidos!", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(PedidoCog(bot))