import discord
from discord.ext import commands
import logging

from ..config import CANAL_PEDIDO_ID, CARGOS_AUTORIZADOS, ID_MARCADOR_PEDIDO # Importação relativa corrigida
from ..utils.utils_embeds import criar_embed # Importação relativa corrigida

logger = logging.getLogger(__name__)

class PedidoModal(discord.ui.Modal, title="Pedidos The Continental"):
    cliente = discord.ui.TextInput(
        label="Cliente",
        placeholder="Nome do cliente.",
        style=discord.TextStyle.short,
        required=True,
    )
    fuzil = discord.ui.TextInput(
        label="M16 (Fuzil)",
        placeholder="Quantidade de armas.",
        style=discord.TextStyle.short,
        required=False,
    )
    ia2 = discord.ui.TextInput(
        label="IA2",
        placeholder="Quantidade de armas.",
        style=discord.TextStyle.short,
        required=False,
    )

    def __init__(self, bot: commands.Bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        dados = {}
        if self.fuzil.value.strip():
            dados["M16 (Fuzil)"] = self.fuzil.value.strip()
        if self.ia2.value.strip():
            dados["IA2"] = self.ia2.value.strip()

        if not dados:
            await interaction.response.send_message(
                "❌ Você precisa preencher a quantidade de pelo menos uma arma.", ephemeral=True
            )
            logger.warning(f"PedidoModal: Nenhum dado de arma preenchido por {interaction.user.display_name}.")
            return

        view = EscolhaPedidoView(
            cliente=self.cliente.value.strip(),
            dados=dados,
            bot=self.bot,
            user=interaction.user,
        )

        await interaction.response.send_message(
            "✅ Pedido recebido! Agora escolha o tipo do pedido:",
            view=view,
            ephemeral=True,
        )
        logger.info(f"PedidoModal: Dados iniciais de pedido recebidos de {interaction.user.display_name}.")

class EscolhaPedidoView(discord.ui.View):
    def __init__(self, cliente, dados, bot, user):
        super().__init__(timeout=60)
        self.cliente = cliente
        self.dados = dados
        self.bot = bot
        self.user = user

    @discord.ui.button(
        label="📦 Pedido Normal",
        style=discord.ButtonStyle.primary,
        custom_id="botao_pedido_normal"
    )
    async def pedido_normal(self, interaction: discord.Interaction, button: discord.ui.Button):
        from ..cogs.pedido_cog import processar_pedido_logic # Importar a lógica do cog aqui para evitar importação circular
        await interaction.response.send_modal(
            EntregaModal(self.cliente, self.dados, self.bot, self.user, parceria=False)
        )
        self.stop()
        logger.info(f"EscolhaPedidoView: Pedido normal selecionado por {interaction.user.display_name}.")

    @discord.ui.button(
        label="🤝 Pedido Parceria",
        style=discord.ButtonStyle.success,
        custom_id="botao_pedido_parceria"
    )
    async def pedido_parceria(self, interaction: discord.Interaction, button: discord.ui.Button):
        from ..cogs.pedido_cog import processar_pedido_logic # Importar a lógica do cog aqui para evitar importação circular
        await interaction.response.send_modal(
            EntregaModal(self.cliente, self.dados, self.bot, self.user, parceria=True)
        )
        self.stop()
        logger.info(f"EscolhaPedidoView: Pedido parceria selecionado por {interaction.user.display_name}.")

class EntregaModal(discord.ui.Modal, title="Previsão de Entrega"):
    entrega = discord.ui.TextInput(
        label="Previsão de Entrega",
        placeholder="Ex: 31/07/2025",
        style=discord.TextStyle.short,
        required=True,
    )

    def __init__(self, cliente, dados, bot, user, parceria: bool):
        super().__init__()
        self.cliente = cliente
        self.dados = dados
        self.bot = bot
        self.user = user
        self.parceria = parceria

    async def on_submit(self, interaction: discord.Interaction):
        from ..cogs.pedido_cog import processar_pedido_logic # Importar a lógica do cog aqui para evitar importação circular
        await processar_pedido_logic(
            interaction, self.cliente, self.dados, self.bot, self.user, self.entrega.value, self.parceria
        )
        logger.info(f"EntregaModal: Previsão de entrega '{self.entrega.value}' enviada por {interaction.user.display_name}.")

class PedidoView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="📦 Fazer Pedido de Arma",
        style=discord.ButtonStyle.primary,
        custom_id="botao_pedido"
    )
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        cargos = [role.name.lower() for role in interaction.user.roles]
        if not any(cargo in CARGOS_AUTORIZADOS for cargo in cargos):
            await interaction.response.send_message(
                "❌ Você não tem permissão para fazer um pedido.", ephemeral=True
            )
            logger.warning(f"PedidoView: Tentativa de fazer pedido sem permissão por {interaction.user.display_name}.")
            return

        try:
            await interaction.response.send_modal(PedidoModal(self.bot))
            try:
                if interaction.message:
                    await interaction.message.delete()
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Erro ao abrir formulário de pedido: {e}", exc_info=True)
            try:
                await interaction.response.send_message(f"❌ Não foi possível abrir o formulário: {e}", ephemeral=True)
            except Exception:
                try:
                    await interaction.followup.send("❌ Não foi possível abrir o formulário.", ephemeral=True)
                except Exception:
                    pass