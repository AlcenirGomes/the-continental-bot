import asyncio
import discord
import logging
import os
from discord.ui import Modal, TextInput, View, Button
from datetime import datetime

from config import ID_MARCADOR, CATEGORIA_FARM_ID
from utils.utils_prints import registrar_print
from utils.utils_embeds import criar_embed
from utils.utils_cloudinary import salvar_print_cloudinary

logger = logging.getLogger(__name__)


class FarmModalParte1(Modal, title='Coleta de Materiais - Parte 1'):
    def __init__(self):
        super().__init__()
        self.cabo     = TextInput(label='Cabo',     required=True)
        self.clip     = TextInput(label='Clip',     required=True)
        self.culatra  = TextInput(label='Culatra',  required=True)
        self.ferrolho = TextInput(label='Ferrolho', required=True)
        self.slide    = TextInput(label='Slide',    required=True)
        for campo in (self.cabo, self.clip, self.culatra, self.ferrolho, self.slide):
            self.add_item(campo)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            valores_parte1 = {
                'Cabo':     self.cabo.value.strip(),
                'Clip':     self.clip.value.strip(),
                'Culatra':  self.culatra.value.strip(),
                'Ferrolho': self.ferrolho.value.strip(),
                'Slide':    self.slide.value.strip(),
            }
            await interaction.response.send_message(
                'Parte 1 recebida! Clique no botao abaixo para informar o Titanio.',
                view=ContinuarView(valores_parte1),
                ephemeral=True,
            )
        except Exception:
            logger.exception('Erro ao processar FarmModalParte1')
            try:
                await interaction.response.send_message('Erro ao processar Parte 1.', ephemeral=True)
            except discord.HTTPException:
                pass


class FarmModalParte2(Modal, title='Coleta de Materiais - Parte 2'):
    def __init__(self, valores_parte1):
        super().__init__()
        self.valores_parte1 = valores_parte1
        self.titanio = TextInput(label='Titanio', required=True)
        self.add_item(self.titanio)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            valores = {k: int(v) for k, v in self.valores_parte1.items()}
            valores['Titanio'] = int(self.titanio.value.strip())
        except ValueError:
            await interaction.response.send_message('Todos os valores devem ser numeros inteiros.', ephemeral=True)
            return

        await interaction.response.send_message('Valores recebidos! Agora envie um print (imagem) neste canal.', ephemeral=True)

        def check_img(msg):
            return (msg.author == interaction.user and msg.channel == interaction.channel and bool(msg.attachments))

        try:
            img_msg = await interaction.client.wait_for('message', check=check_img, timeout=120)
        except asyncio.TimeoutError:
            await interaction.followup.send('Tempo esgotado. Nenhuma imagem recebida.', ephemeral=True)
            return
        except Exception:
            logger.exception('Erro ao aguardar print de %s', interaction.user)
            await interaction.followup.send('Erro ao aguardar imagem.', ephemeral=True)
            return

        anexo        = img_msg.attachments[0]
        cdn_url      = anexo.url
        extensao     = os.path.splitext(anexo.filename)[1] or '.png'
        data_str     = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        nome_arquivo = f'{interaction.user.id}_{data_str}{extensao}'

        await interaction.followup.send('Salvando imagem...', ephemeral=True)

        cloudinary_url = await salvar_print_cloudinary(cdn_url, nome_arquivo)

        if not cloudinary_url:
            await interaction.followup.send('Nao consegui salvar permanentemente. Continuando com URL temporaria.', ephemeral=True)

        url_para_embed = cloudinary_url or cdn_url

        registrar_print(user_id=interaction.user.id, cdn_url=cdn_url, nome_arquivo=nome_arquivo, cloudinary_url=cloudinary_url)

        try:
            await img_msg.delete()
        except discord.HTTPException:
            pass

        arquivo = await anexo.to_file()

        apelido = interaction.user.nick or interaction.user.name
        if ' | ' in apelido:
            base_nome, passaporte = apelido.replace('M ', '').split(' | ', 1)
            nome_canal_esperado = f'M{base_nome.lower().replace(chr(32), chr(45))}-{passaporte}'
        else:
            nome_canal_esperado = apelido.lower().replace(' ', '-')

        canal = interaction.channel
        user_no_topico = canal.topic and str(interaction.user.id) in canal.topic
        if not user_no_topico and canal.name != nome_canal_esperado:
            try:
                await canal.edit(name=nome_canal_esperado)
            except discord.Forbidden:
                await interaction.followup.send('Nao consegui renomear o canal.', ephemeral=True)

        embed = criar_embed(
            title='Coleta de Materiais',
            description=f'{interaction.user.mention} enviou os seguintes dados:',
            color=0x272727,
            footer_text=f'Enviado por {interaction.user.name}',
        )
        for item, valor in valores.items():
            embed.add_field(name=item, value=str(valor), inline=True)

        embed.set_image(url=f'attachment://{arquivo.filename}')
        embed.add_field(name='Print Enviado', value=f'[Clique aqui para visualizar]({url_para_embed})', inline=False)

        mensagem_embed = await canal.send(content=interaction.user.mention, embed=embed, file=arquivo)

        from views.coleta import AvaliacaoView
        await mensagem_embed.edit(view=AvaliacaoView(mensagem_embed, embed, interaction.user))
        await canal.send('Dados enviados com sucesso!', delete_after=10)

        logger.info('Coleta registrada - user=%s cloudinary=%s', interaction.user.id, cloudinary_url or 'fallback')


class ContinuarView(discord.ui.View):
    def __init__(self, valores_parte1):
        super().__init__(timeout=60)
        self.valores_parte1 = valores_parte1

    @discord.ui.button(label='Continuar com Titanio', style=discord.ButtonStyle.primary, custom_id='continuar_farm')
    async def continuar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(FarmModalParte2(self.valores_parte1))


class FarmView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Abrir Formulario de Coleta', style=discord.ButtonStyle.primary, custom_id='botao_farm')
    async def open_modal(self, interaction: discord.Interaction, button: Button):
        try:
            await interaction.response.send_modal(FarmModalParte1())
            try:
                await interaction.message.delete()
            except discord.HTTPException:
                pass
        except Exception:
            logger.exception('Erro ao abrir FarmModalParte1')
            try:
                await interaction.response.send_message('Erro ao abrir o formulario.', ephemeral=True)
            except discord.HTTPException:
                pass


async def enviar_botao_se_necessario(canal, bot_user):
    if canal.category_id != CATEGORIA_FARM_ID:
        return
    try:
        async for msg in canal.history(limit=50):
            if (msg.author == bot_user and msg.components and (msg.content or '').strip() == ID_MARCADOR):
                logger.info('Botao ja existe em #%s, ignorando.', canal.name)
                return
        async for msg in canal.history(limit=50):
            if msg.author == bot_user and msg.components:
                try:
                    await msg.delete()
                except discord.HTTPException:
                    pass
        embed = criar_embed(title='Entrega do Farm Semanal', description='Clique no botao abaixo para entregar seu farm.', color=0x272727)
        await canal.send(content=ID_MARCADOR, embed=embed, view=FarmView())
        logger.info('Botao de farm enviado em #%s', canal.name)
    except discord.Forbidden:
        logger.warning('Sem permissao em #%s', canal.name)
    except Exception:
        logger.exception('Erro ao enviar botao em #%s', canal.name)


async def enviar_botao_farm(canal):
    await enviar_botao_se_necessario(canal, canal.guild.me)