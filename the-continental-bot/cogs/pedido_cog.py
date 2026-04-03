import discord
from discord.ext import commands
from discord import app_commands
import logging

from ..views.pedido import PedidoView
from ..utils.utils_embeds import criar_embed
from ..utils.utils_discord import limpar_e_enviar_view
from ..config import CANAL_PEDIDO_ID, ID_MARCADOR_PEDIDO, CARGOS_AUTORIZADOS

logger = logging.getLogger(__name__)

PRECOS = {
    "M16 (Fuzil)": 180000.00,
    "IA2": 140000.00,
}
COMISSAO_PERCENTUAL = 0.10

def calcular_preco(item: str, quantidade: int, parceria: bool = False) -> float:
    if item == "IA2":
        return 140000.0

    if parceria:
        return 160000.0
    if quantidade <= 2:
        return 180000.0
    elif 3 <= quantidade <= 6:
        return 170000.0
    else:
        return 160000.0

async def processar_pedido_logic(interaction: discord.Interaction, cliente: str, dados: dict, bot: commands.Bot, user: discord.User, entrega: str, parceria: bool):
    canal = bot.get_channel(CANAL_PEDIDO_ID)
    if not canal:
        await interaction.followup.send(
            "❌ Canal de pedido não encontrado.", ephemeral=True
        )
        logger.warning(f"Processar pedido: Canal de pedido (ID: {CANAL_PEDIDO_ID}) não encontrado.")
        return

    try:
        # Limpar mensagens antigas que não são embeds de pedido ou fixadas
        async for msg in canal.history(limit=100):
            if msg.pinned:
                continue
            if not msg.embeds or not (msg.embeds[0].title.startswith("📦") or msg.embeds[0].title.startswith("🤝")):
                try:
                    await msg.delete()
                except discord.Forbidden:
                    logger.warning(f"Sem permissão para deletar mensagem em {canal.name} (ID: {canal.id}).")
                except Exception as e:
                    logger.error(f"Erro ao deletar mensagem em {canal.name} (ID: {canal.id}): {e}", exc_info=True)

        total = 0
        campos_validos = {}

        for item, valor in dados.items():
            if not valor:
                continue
            try:
                qtd = int(valor)
                if item not in PRECOS:
                    await interaction.followup.send(
                        f"❌ A arma **{item}** não está disponível.", ephemeral=True
                    )
                    logger.warning(f"Item '{item}' não disponível no pedido de {user.display_name}.")
                    return
                preco_unitario = calcular_preco(item, qtd, parceria)
                subtotal = preco_unitario * qtd
                campos_validos[item] = (qtd, subtotal, preco_unitario)
                total += subtotal
            except ValueError:
                # CORRIGIDO: Mensagem de erro mais específica
                await interaction.followup.send(
                    f"❌ Quantidade inválida para **{item}**. Por favor, insira um número inteiro.", ephemeral=True
                )
                logger.warning(f"Quantidade inválida para '{item}' no pedido de {user.display_name}.")
                return

        comissao = total * COMISSAO_PERCENTUAL

        if parceria:
            titulo = "🤝 Pedido de Parceria"
            descricao = "**Tipo de Pedido: Parceria **"
        else:
            titulo = "📦 Pedido de Arma"
            descricao = "**Tipo de Pedido: Venda Normal**"

        embed = criar_embed(
            title=titulo,
            description=descricao,
            color=discord.Color.green() if parceria else 0x272727,
            footer_text=f"Pedido feito por {user.display_name}",
        )
        embed.add_field(name="👤 Cliente", value=cliente, inline=False)
        for nome, (qtd, subtotal, preco_unitario) in campos_validos.items():
            embed.add_field(
                name=nome,
                value=f"Quantidade: {qtd} = R${subtotal:,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", "."),
                inline=False,
            )
        embed.add_field(
            name="💵 Valor Total do Pedido",
            value=f"R${total:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            inline=False,
        )
        embed.add_field(
            name="💸 Comissão do Vendedor (10%)",
            value=f"R${comissao:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", "."),
            inline=False,
        )
        embed.add_field(
            name="📅 Previsão de Entrega", value=entrega or "Não informada", inline=False
        )

        await canal.send(embed=embed)
        logger.info(f"✅ Pedido registrado por {user.display_name} para {cliente}")

        # Recriar o botão de pedido após o envio do pedido
        embed_recriar_pedido = criar_embed(
            title="📦 Fazer outro pedido",
            description="Clique no botão abaixo para abrir novamente o formulário.",
            color=0x272727,
        )
        await limpar_e_enviar_view(
            canal,
            bot.user,
            ID_MARCADOR_PEDIDO,
            embed_recriar_pedido,
            PedidoView(bot),
            getattr(bot, "_suppress_recreate_pedido", set()),
            canal.id
        )

        try:
            if interaction.message:
                await interaction.message.delete()
        except discord.Forbidden:
            logger.warning(f"Sem permissão para deletar mensagem de interação em {canal.name} (ID: {canal.id}).")
        except Exception as e:
            logger.error(f"Erro ao deletar mensagem de interação em {canal.name} (ID: {canal.id}): {e}", exc_info=True)

    except Exception as e:
        logger.error(f"❌ Erro ao processar pedido: {e}", exc_info=True)
        await interaction.followup.send("❌ Erro ao processar seu pedido.", ephemeral=True)

class PedidoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="pedido", description="Força o envio do botão de pedidos no canal de pedidos")
    async def pedido_command(self, interaction: discord.Interaction):
        canal = self.bot.get_channel(CANAL_PEDIDO_ID)
        if not canal:
            await interaction.response.send_message("❌ Canal de pedidos não encontrado.", ephemeral=True)
            logger.warning(f"Comando /pedido: Canal de pedidos (ID: {CANAL_PEDIDO_ID}) não encontrado.")
            return

        embed = criar_embed(
            title="📦 Pedidos de Armas",
            description="Clique no botão abaixo para solicitar um orçamento.",
            color=0x272727,
        )
        view = PedidoView(self.bot)

        await limpar_e_enviar_view(
            canal,
            self.bot.user,
            ID_MARCADOR_PEDIDO,
            embed,
            view,
            getattr(self.bot, "_suppress_recreate_pedido", set()),
            canal.id
        )
        await interaction.response.send_message("✅ Botão de pedidos recriado no canal de pedidos!", ephemeral=True)
        logger.info(f"Comando /pedido: Botão de pedidos recriado por {interaction.user.display_name}.")

    @commands.Cog.listener()
    async def on_ready(self):
        pass

async def setup(bot: commands.Bot):
    await bot.add_cog(PedidoCog(bot))