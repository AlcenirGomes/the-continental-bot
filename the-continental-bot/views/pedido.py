import discord
import logging
from discord.ext import commands

from config import CANAL_PEDIDO_ID, CARGOS_AUTORIZADOS, ID_MARCADOR_PEDIDO
from utils.utils_embeds import criar_embed

logger = logging.getLogger(__name__)

PRECOS = {'M16 (Fuzil)': 180000.00, 'IA2': 140000.00}
PRECOS_FIXOS = {'M16 (Fuzil)': 180000.00, 'IA2': 140000.00}
COMISSAO_PERCENTUAL = 0.10


def calcular_preco(item, quantidade, parceria=False):
    if item == 'IA2':
        return 140000.0
    if parceria:
        return 160000.0
    if quantidade <= 2:
        return 180000.0
    elif 3 <= quantidade <= 6:
        return 170000.0
    return 160000.0


def formatar_real(valor):
    return f'R${valor:_.2f}'.replace('.', ',').replace('_', '.')


class PedidoModal(discord.ui.Modal, title='Pedidos The Continental'):
    cliente = discord.ui.TextInput(label='Cliente',     placeholder='Nome do cliente.',     style=discord.TextStyle.short, required=True)
    fuzil   = discord.ui.TextInput(label='M16 (Fuzil)', placeholder='Quantidade de armas.', style=discord.TextStyle.short, required=False)
    ia2     = discord.ui.TextInput(label='IA2',         placeholder='Quantidade de armas.', style=discord.TextStyle.short, required=False)

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        dados = {}
        if self.fuzil.value.strip():
            dados['M16 (Fuzil)'] = self.fuzil.value.strip()
        if self.ia2.value.strip():
            dados['IA2'] = self.ia2.value.strip()
        if not dados:
            await interaction.response.send_message('Preencha a quantidade de pelo menos uma arma.', ephemeral=True)
            return
        await interaction.response.send_message('Pedido recebido! Agora escolha o tipo do pedido:', view=EscolhaPedidoView(cliente=self.cliente.value.strip(), dados=dados, bot=self.bot, user=interaction.user), ephemeral=True)


class EscolhaPedidoView(discord.ui.View):
    def __init__(self, cliente, dados, bot, user):
        super().__init__(timeout=60)
        self.cliente = cliente
        self.dados   = dados
        self.bot     = bot
        self.user    = user

    @discord.ui.button(label='Pedido Normal',   style=discord.ButtonStyle.primary,   custom_id='botao_pedido_normal',   row=0)
    async def pedido_normal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EntregaModal(self.cliente, self.dados, self.bot, self.user, modo='normal'))
        self.stop()

    @discord.ui.button(label='Pedido Parceria', style=discord.ButtonStyle.success,   custom_id='botao_pedido_parceria', row=0)
    async def pedido_parceria(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EntregaModal(self.cliente, self.dados, self.bot, self.user, modo='parceria'))
        self.stop()

    @discord.ui.button(label='Venda Fixa',      style=discord.ButtonStyle.secondary, custom_id='botao_venda_fixa',      row=0)
    async def venda_fixa(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EntregaModal(self.cliente, self.dados, self.bot, self.user, modo='fixa'))
        self.stop()


class EntregaModal(discord.ui.Modal, title='Previsao de Entrega'):
    entrega = discord.ui.TextInput(label='Previsao de Entrega', placeholder='Ex: 31/07/2025', style=discord.TextStyle.short, required=True)

    def __init__(self, cliente, dados, bot, user, modo):
        super().__init__()
        self.cliente = cliente
        self.dados   = dados
        self.bot     = bot
        self.user    = user
        self.modo    = modo

    async def on_submit(self, interaction: discord.Interaction):
        modos = {'normal': 'Pedido Normal', 'parceria': 'Pedido Parceria', 'fixa': 'Venda Fixa'}
        await interaction.response.send_message(f'O {modos.get(self.modo, self.modo)} tera comissao de 10%?', view=ComissaoView(self.cliente, self.dados, self.bot, self.user, self.entrega.value.strip(), self.modo), ephemeral=True)


class ComissaoView(discord.ui.View):
    def __init__(self, cliente, dados, bot, user, entrega, modo):
        super().__init__(timeout=60)
        self.cliente = cliente
        self.dados   = dados
        self.bot     = bot
        self.user    = user
        self.entrega = entrega
        self.modo    = modo

    @discord.ui.button(label='Sim, com comissao',  style=discord.ButtonStyle.success, custom_id='comissao_sim')
    async def com_comissao(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._processar(interaction, com_comissao=True)

    @discord.ui.button(label='Nao, sem comissao', style=discord.ButtonStyle.danger,  custom_id='comissao_nao')
    async def sem_comissao(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._processar(interaction, com_comissao=False)

    async def _processar(self, interaction, com_comissao):
        self.stop()
        if self.modo == 'fixa':
            await processar_venda_fixa(interaction, self.bot, self.user, self.cliente, self.dados, self.entrega, com_comissao)
        else:
            await processar_pedido(interaction, self.cliente, self.dados, self.bot, self.user, self.entrega, self.modo == 'parceria', com_comissao)


async def _limpar_historico_pedido(canal):
    async for msg in canal.history(limit=100):
        if msg.pinned:
            continue
        if msg.embeds and msg.embeds[0].title and any(msg.embeds[0].title.startswith(p) for p in ('Pedido', 'Venda', 'Parceria')):
            continue
        try:
            await msg.delete()
        except discord.HTTPException:
            pass


async def _recriar_botao_pedido(canal, bot):
    async for msg in canal.history(limit=50):
        if msg.author == bot.user and msg.components:
            try:
                await msg.delete()
            except discord.HTTPException:
                pass
    embed = criar_embed(title='Fazer outro pedido', description='Clique no botao abaixo para abrir novamente o formulario.', color=0x272727)
    await canal.send(content=ID_MARCADOR_PEDIDO, embed=embed, view=PedidoView(bot))


async def processar_pedido(interaction, cliente, dados, bot, user, entrega, parceria, com_comissao):
    canal = bot.get_channel(CANAL_PEDIDO_ID)
    if not canal:
        await interaction.response.send_message('Canal de pedido nao encontrado.', ephemeral=True)
        return
    await interaction.response.defer()
    if not hasattr(bot, '_suppress_recreate_pedido'):
        bot._suppress_recreate_pedido = set()
    bot._suppress_recreate_pedido.add(canal.id)
    try:
        await _limpar_historico_pedido(canal)
        total = 0.0
        campos_validos = {}
        for item, valor in dados.items():
            if not valor:
                continue
            try:
                qtd = int(valor)
            except ValueError:
                await interaction.followup.send(f'Quantidade invalida para {item}.', ephemeral=True)
                return
            if item not in PRECOS:
                await interaction.followup.send(f'A arma {item} nao esta disponivel.', ephemeral=True)
                return
            preco_unitario = calcular_preco(item, qtd, parceria)
            subtotal = preco_unitario * qtd
            campos_validos[item] = (qtd, subtotal)
            total += subtotal
        comissao = total * COMISSAO_PERCENTUAL if com_comissao else 0.0
        titulo    = 'Pedido de Parceria' if parceria else 'Pedido de Arma'
        descricao = 'Tipo de Pedido: Parceria' if parceria else 'Tipo de Pedido: Venda Normal'
        embed = criar_embed(title=titulo, description=descricao, color=discord.Color.green() if parceria else 0x272727, footer_text=f'Pedido feito por {user.display_name}')
        embed.add_field(name='Cliente', value=cliente, inline=False)
        for nome, (qtd, subtotal) in campos_validos.items():
            embed.add_field(name=nome, value=f'Quantidade: {qtd} = {formatar_real(subtotal)}', inline=False)
        embed.add_field(name='Valor Total do Pedido', value=formatar_real(total), inline=False)
        if com_comissao:
            embed.add_field(name='Comissao do Vendedor (10%)', value=formatar_real(comissao), inline=False)
        else:
            embed.add_field(name='Comissao', value='Sem comissao', inline=False)
        embed.add_field(name='Previsao de Entrega', value=entrega or 'Nao informada', inline=False)
        await canal.send(embed=embed)
        logger.info('Pedido por %s para %s | parceria=%s comissao=%s', user.display_name, cliente, parceria, com_comissao)
        await _recriar_botao_pedido(canal, bot)
        try:
            if interaction.message:
                await interaction.message.delete()
        except discord.HTTPException:
            pass
    finally:
        bot._suppress_recreate_pedido.discard(canal.id)


async def processar_venda_fixa(interaction, bot, user, cliente, dados, entrega, com_comissao):
    canal = bot.get_channel(CANAL_PEDIDO_ID)
    if not canal:
        await interaction.response.send_message('Canal de pedido nao encontrado.', ephemeral=True)
        return
    await interaction.response.defer()
    if not hasattr(bot, '_suppress_recreate_pedido'):
        bot._suppress_recreate_pedido = set()
    bot._suppress_recreate_pedido.add(canal.id)
    try:
        await _limpar_historico_pedido(canal)
        total  = 0.0
        campos = []
        for item, valor in dados.items():
            if not valor:
                continue
            try:
                qtd = int(valor)
            except ValueError:
                await interaction.followup.send(f'Quantidade invalida para {item}.', ephemeral=True)
                return
            if item not in PRECOS_FIXOS:
                await interaction.followup.send(f'A arma {item} nao esta disponivel.', ephemeral=True)
                return
            subtotal = PRECOS_FIXOS[item] * qtd
            campos.append((item, qtd, subtotal))
            total += subtotal
        comissao = total * COMISSAO_PERCENTUAL if com_comissao else 0.0
        embed = criar_embed(title='Venda Fixa', description='Tipo de Pedido: Venda com Preco Fixo. Precos sem desconto ou variacao por quantidade.', color=0xf39c12, footer_text=f'Registrado por {user.display_name}')
        embed.add_field(name='Cliente', value=cliente, inline=False)
        for nome, qtd, subtotal in campos:
            embed.add_field(name=nome, value=f'Quantidade: {qtd}\nPreco unitario: {formatar_real(PRECOS_FIXOS[nome])}\nSubtotal: {formatar_real(subtotal)}', inline=True)
        embed.add_field(name='Valor Total', value=formatar_real(total), inline=False)
        if com_comissao:
            embed.add_field(name='Comissao do Vendedor (10%)', value=formatar_real(comissao), inline=False)
        else:
            embed.add_field(name='Comissao', value='Sem comissao', inline=False)
        embed.add_field(name='Previsao de Entrega', value=entrega or 'Nao informada', inline=False)
        await canal.send(embed=embed)
        logger.info('Venda fixa por %s para %s total=%s comissao=%s', user.display_name, cliente, formatar_real(total), com_comissao)
        await _recriar_botao_pedido(canal, bot)
        try:
            if interaction.message:
                await interaction.message.delete()
        except discord.HTTPException:
            pass
    finally:
        bot._suppress_recreate_pedido.discard(canal.id)


class PedidoView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label='Fazer Pedido de Arma', style=discord.ButtonStyle.primary, custom_id='botao_pedido')
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        cargos = [role.name.lower() for role in interaction.user.roles]
        if not any(cargo in CARGOS_AUTORIZADOS for cargo in cargos):
            await interaction.response.send_message('Voce nao tem permissao para fazer um pedido.', ephemeral=True)
            return
        try:
            await interaction.response.send_modal(PedidoModal(self.bot))
            try:
                await interaction.message.delete()
            except discord.HTTPException:
                pass
        except Exception:
            logger.exception('Erro ao abrir PedidoModal')
            try:
                await interaction.followup.send('Nao foi possivel abrir o formulario.', ephemeral=True)
            except discord.HTTPException:
                pass