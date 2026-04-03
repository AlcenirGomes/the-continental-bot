import discord
from discord.ext import commands
from discord import app_commands

from views.pedido import PedidoView, _recriar_botao_pedido
from config import CANAL_PEDIDO_ID


class PedidoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="pedido", description="Força o envio do botão de pedidos")
    async def pedido(self, interaction: discord.Interaction):
        canal = self.bot.get_channel(CANAL_PEDIDO_ID)
        if not canal:
            await interaction.response.send_message("❌ Canal de pedidos não encontrado.", ephemeral=True)
            return
        await _recriar_botao_pedido(canal, self.bot)
        await interaction.response.send_message("✅ Botão de pedidos recriado!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(PedidoCog(bot))