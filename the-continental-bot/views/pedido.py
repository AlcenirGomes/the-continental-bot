import discord
from discord.ext import commands
from utils_embeds import criar_embed
from config import CANAL_PEDIDO_ID, CARGOS_AUTORIZADOS, ID_MARCADOR_PEDIDO

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
        await interaction.response.send_modal(
            EntregaModal(self.cliente, self.dados, self.bot, self.user, parceria=False)
        )
        self.stop()

    @discord.ui.button(
        label="🤝 Pedido Parceria",
        style=discord.ButtonStyle.success,
        custom_id="botao_pedido_parceria"
    )
    async def pedido_parceria(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            EntregaModal(self.cliente, self.dados, self.bot, self.user, parceria=True)
        )
        self.stop()

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
        await processar_pedido(
            interaction, self.cliente, self.dados, self.bot, self.user, self.entrega.value, self.parceria
        )

async def processar_pedido(interaction, cliente, dados, bot, user, entrega, parceria: bool):
    canal = bot.get_channel(CANAL_PEDIDO_ID)
    if not canal:
        await interaction.response.send_message(
            "❌ Canal de pedido não encontrado.", ephemeral=True
        )
        return

    await interaction.response.defer()

    if not hasattr(bot, "_suppress_recreate_pedido"):
        bot._suppress_recreate_pedido = set()
    bot._suppress_recreate_pedido.add(canal.id)

    try:
        async for msg in canal.history(limit=100):
            if msg.pinned:
                continue
            if not msg.embeds or not (msg.embeds[0].title.startswith("📦") or msg.embeds[0].title.startswith("🤝")):
                try:
                    await msg.delete()
                except Exception:
                    pass

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
                    return
                preco_unitario = calcular_preco(item, qtd, parceria)
                subtotal = preco_unitario * qtd
                campos_validos[item] = (qtd, subtotal, preco_unitario)
                total += subtotal
            except ValueError:
                await interaction.followup.send(
                    f"❌ Quantidade inválida para {item}.", ephemeral=True
                )
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
        print(f"✅ Pedido registrado por {user.display_name} para {cliente}")

        async for msg in canal.history(limit=50):
            if msg.author == bot.user and msg.components:
                try:
                    await msg.delete()
                except Exception:
                    pass

        await canal.send(
            content=ID_MARCADOR_PEDIDO, # Usar ID_MARCADOR_PEDIDO
            embed=criar_embed(
                title="📦 Fazer outro pedido",
                description="Clique no botão abaixo para abrir novamente o formulário.",
                color=0x272727,
            ),
            view=PedidoView(bot),
        )

        try:
            if interaction.message:
                await interaction.message.delete()
        except Exception:
            pass

    finally:
        try:
            bot._suppress_recreate_pedido.discard(canal.id)
        except Exception:
            pass

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
            return

        try:
            await interaction.response.send_modal(PedidoModal(self.bot))
            try:
                await interaction.message.delete()
            except Exception:
                pass
        except Exception as e:
            try:
                await interaction.response.send_message(f"❌ Não foi possível abrir o formulário: {e}", ephemeral=True)
            except Exception:
                try:
                    await interaction.followup.send("❌ Não foi possível abrir o formulário.", ephemeral=True)
                except Exception:
                    pass

class Pedido(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        canal = self.bot.get_channel(CANAL_PEDIDO_ID)
        if canal:
            if not hasattr(self.bot, "_suppress_recreate_pedido"):
                self.bot._suppress_recreate_pedido = set()
            self.bot._suppress_recreate_pedido.add(canal.id)
            try:
                async for msg in canal.history(limit=50):
                    if msg.author == self.bot.user and msg.components:
                        try:
                            await msg.delete()
                        except Exception:
                            pass

                embed = criar_embed(
                    title="📦 Pedidos de Armas",
                    description="Clique no botão abaixo para solicitar um orçamento.",
                    color=0x272727,
                )
                await canal.send(content=ID_MARCADOR_PEDIDO, embed=embed, view=PedidoView(self.bot)) # Usar ID_MARCADOR_PEDIDO
                print("✅ Botão de pedido enviado no canal de pedidos.")
            finally:
                try:
                    self.bot._suppress_recreate_pedido.discard(canal.id)
                except Exception:
                    pass

async def setup(bot):
    bot.add_view(PedidoView(bot))
    await bot.add_cog(Pedido(bot))