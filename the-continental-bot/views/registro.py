import discord
import logging
from discord.ui import View, Button

from config import (CATEGORIA_FARM_ID, CARGOS_AUTORIZADOS, CANAL_REGISTRO_ID, CANAL_APROVACAO_ID, ID_MARCADOR_REGISTRO)
from utils.utils_embeds import criar_embed

logger = logging.getLogger(__name__)


class RegistroModal(discord.ui.Modal, title='Registro de Membro'):
    def __init__(self):
        super().__init__()
        self.nome       = discord.ui.TextInput(label='Nome',       required=True)
        self.passaporte = discord.ui.TextInput(label='Passaporte', required=True)
        self.recrutador = discord.ui.TextInput(label='Recrutador', required=True)
        for campo in (self.nome, self.passaporte, self.recrutador):
            self.add_item(campo)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            embed = criar_embed(title='Novo Registro', description=f'Novo registro enviado por {interaction.user.mention}', color=0x272727, footer_text=f'ID do usuario: {interaction.user.id}')
            embed.add_field(name='Nome',       value=self.nome.value,       inline=False)
            embed.add_field(name='Passaporte', value=self.passaporte.value, inline=False)
            embed.add_field(name='Recrutador', value=self.recrutador.value, inline=False)
            view = AvaliacaoRegistroView(interaction.user, self.nome.value, self.passaporte.value)
            canal_aprovacao = interaction.guild.get_channel(CANAL_APROVACAO_ID)
            if canal_aprovacao:
                await canal_aprovacao.send(embed=embed, view=view)
                await interaction.response.send_message('Seu registro foi enviado para aprovacao!', ephemeral=True)
            else:
                await interaction.response.send_message('Canal de aprovacao nao encontrado.', ephemeral=True)
        except Exception:
            logger.exception('Erro ao submeter RegistroModal')
            try:
                await interaction.response.send_message('Erro ao enviar registro.', ephemeral=True)
            except discord.HTTPException:
                pass


class AvaliacaoRegistroView(View):
    def __init__(self, user, nome, passaporte):
        super().__init__(timeout=None)
        self.user       = user
        self.nome       = nome
        self.passaporte = passaporte

    async def verificar_permissao(self, interaction: discord.Interaction):
        cargos = [r.name.lower() for r in interaction.user.roles]
        if not any(cargo in CARGOS_AUTORIZADOS for cargo in cargos):
            await interaction.response.send_message('Voce nao tem permissao para aprovar/reprovar registros.', ephemeral=True)
            return False
        return True

    @discord.ui.button(label='Aprovar',  style=discord.ButtonStyle.success, custom_id='aprovar_registro')
    async def aprovar(self, interaction: discord.Interaction, button: Button):
        if not await self.verificar_permissao(interaction):
            return
        await self.finalizar_registro(interaction, aprovado=True)

    @discord.ui.button(label='Reprovar', style=discord.ButtonStyle.danger,  custom_id='reprovar_registro')
    async def reprovar(self, interaction: discord.Interaction, button: Button):
        if not await self.verificar_permissao(interaction):
            return
        await self.finalizar_registro(interaction, aprovado=False)

    async def finalizar_registro(self, interaction: discord.Interaction, aprovado: bool):
        try:
            await interaction.response.defer(ephemeral=True)
            mensagem = interaction.message
            embed = mensagem.embeds[0] if (mensagem and mensagem.embeds) else criar_embed(title='Registro', description='Registro processado.', color=0x272727)
            if aprovado:
                cor          = 0x2ecc71
                status_texto = 'Aprovado'
                try:
                    await self.user.edit(nick=f'M {self.nome} | {self.passaporte}')
                except discord.Forbidden:
                    await interaction.followup.send('Nao consegui mudar o nick.', ephemeral=True)
                except discord.HTTPException as e:
                    await interaction.followup.send(f'Erro ao mudar nick: {e}', ephemeral=True)
                cargo_membro = discord.utils.get(interaction.guild.roles, name='Membro')
                if cargo_membro:
                    try:
                        await self.user.add_roles(cargo_membro)
                    except discord.Forbidden:
                        await interaction.followup.send('Nao consegui atribuir o cargo.', ephemeral=True)
                    except discord.HTTPException as e:
                        await interaction.followup.send(f'Erro ao atribuir cargo: {e}', ephemeral=True)
                categoria = interaction.guild.get_channel(CATEGORIA_FARM_ID)
                if categoria:
                    nome_canal = f'M{self.nome.lower().replace(chr(32), chr(45))}-{self.passaporte}'
                    overwrites = {
                        interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                        self.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                    }
                    for cargo_nome in ['01', '02', '03', 'gerente']:
                        cargo = discord.utils.get(interaction.guild.roles, name=cargo_nome)
                        if cargo:
                            overwrites[cargo] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
                    canal = None
                    try:
                        canal = await categoria.create_text_channel(name=nome_canal, topic=f'Canal de farm do {self.user.name} | ID: {self.user.id}', overwrites=overwrites)
                    except discord.Forbidden:
                        await interaction.followup.send('Sem permissao para criar canais.', ephemeral=True)
                    except discord.HTTPException as e:
                        await interaction.followup.send(f'Erro ao criar canal: {e}', ephemeral=True)
                    if canal and isinstance(canal, discord.TextChannel) and canal.category_id == CATEGORIA_FARM_ID:
                        from views.farmview import enviar_botao_se_necessario
                        bot = interaction.client
                        if not hasattr(bot, '_suppress_recreate_farm'):
                            bot._suppress_recreate_farm = set()
                        bot._suppress_recreate_farm.add(canal.id)
                        try:
                            await enviar_botao_se_necessario(canal, bot.user)
                        except Exception:
                            logger.exception('Erro ao enviar botao de farm em #%s', canal.name)
                        finally:
                            bot._suppress_recreate_farm.discard(canal.id)
            else:
                cor          = 0xe74c3c
                status_texto = 'Reprovado'
            try:
                embed.color = cor
                embed.add_field(name='Status', value=status_texto, inline=False)
                if mensagem:
                    await mensagem.edit(embed=embed, view=None)
            except discord.HTTPException:
                logger.exception('Erro ao editar embed de registro')
            await interaction.followup.send(f'Registro {status_texto.lower()}!', ephemeral=True)
        except Exception:
            logger.exception('Erro ao finalizar registro')
            try:
                await interaction.followup.send('Erro ao finalizar registro.', ephemeral=True)
            except discord.HTTPException:
                pass


class RegistroView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Registrar Novo Membro', style=discord.ButtonStyle.success, custom_id='registrar')
    async def open_modal(self, interaction: discord.Interaction, button: Button):
        try:
            await interaction.response.send_modal(RegistroModal())
        except Exception:
            logger.exception('Erro ao abrir RegistroModal')
            try:
                await interaction.response.send_message('Erro ao abrir registro.', ephemeral=True)
            except discord.HTTPException:
                pass


async def enviar_botao_registro(bot):
    canal = bot.get_channel(CANAL_REGISTRO_ID)
    if not canal:
        logger.warning('Canal de registro nao encontrado (ID=%s)', CANAL_REGISTRO_ID)
        return
    if not hasattr(bot, '_suppress_recreate_registro'):
        bot._suppress_recreate_registro = set()
    bot._suppress_recreate_registro.add(canal.id)
    try:
        async for msg in canal.history(limit=50):
            if msg.author == bot.user and msg.components:
                try:
                    await msg.delete()
                except discord.HTTPException:
                    pass
        embed = criar_embed(title='Registro de Novos Membros', description='Clique no botao abaixo para registrar-se no cartel.', color=0x272727)
        await canal.send(content=ID_MARCADOR_REGISTRO, embed=embed, view=RegistroView())
        logger.info('Botao de registro enviado.')
    finally:
        bot._suppress_recreate_registro.discard(canal.id)


async def verificar_registro_apagado(message, bot):
    if message.channel.id != CANAL_REGISTRO_ID:
        return
    if not (message.author == bot.user and message.components):
        return
    if message.channel.id in getattr(bot, '_suppress_recreate_registro', set()):
        return
    logger.warning('Botao de registro deletado - recriando.')
    await enviar_botao_registro(bot)