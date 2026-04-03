import discord
from discord.ui import View, Button
import traceback
import logging

from ..config import CATEGORIA_FARM_ID, CARGOS_AUTORIZADOS, ID_MARCADOR_REGISTRO, CANAL_REGISTRO_ID, CANAL_APROVACAO_ID, ID_MARCADOR # Importação relativa corrigida
from ..utils.utils_embeds import criar_embed
from ..utils.utils_discord import limpar_e_enviar_view
# from .farmview import FarmView # FarmView é importada dentro de finalizar_registro para evitar importação circular

logger = logging.getLogger(__name__)

class RegistroModal(discord.ui.Modal, title="Registro de Membro"):
    def __init__(self):
        super().__init__()
        self.nome = discord.ui.TextInput(label="Nome", required=True)
        self.passaporte = discord.ui.TextInput(label="Passaporte", required=True)
        self.recrutador = discord.ui.TextInput(label="Recrutador", required=True)

        self.add_item(self.nome)
        self.add_item(self.passaporte)
        self.add_item(self.recrutador)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            embed = criar_embed(
                title="📋 Novo Registro",
                description=f"Novo registro enviado por {interaction.user.mention}",
                color=0x272727,
                footer_text=f"ID do usuário: {interaction.user.id}",
            )
            embed.add_field(name="👤 Nome", value=self.nome.value, inline=False)
            embed.add_field(name="🪪 Passaporte", value=self.passaporte.value, inline=False)
            embed.add_field(name="👥 Recrutador", value=self.recrutador.value, inline=False)

            view = AvaliacaoRegistroView(interaction.user, self.nome.value, self.passaporte.value)

            canal_aprovacao = interaction.guild.get_channel(CANAL_APROVACAO_ID)
            if canal_aprovacao:
                await canal_aprovacao.send(embed=embed, view=view)
                await interaction.response.send_message("✅ Seu registro foi enviado para aprovação!", ephemeral=True)
                logger.info(f"Registro de {interaction.user.display_name} enviado para aprovação.")
            else:
                await interaction.response.send_message("❌ Canal de aprovação não encontrado.", ephemeral=True)
                logger.warning(f"Canal de aprovação (ID: {CANAL_APROVACAO_ID}) não encontrado ao processar registro de {interaction.user.display_name}.")

        except discord.Forbidden:
            logger.error(f"Sem permissão para enviar mensagem no canal de aprovação (ID: {CANAL_APROVACAO_ID}).", exc_info=True)
            await interaction.response.send_message("❌ Não tenho permissão para enviar mensagens no canal de aprovação.", ephemeral=True)
        except Exception:
            logger.error("Erro ao enviar registro no RegistroModal.", exc_info=True)
            try:
                await interaction.response.send_message("❌ Erro ao enviar registro.", ephemeral=True)
            except Exception:
                pass

class AvaliacaoRegistroView(View):
    def __init__(self, user: discord.Member, nome: str, passaporte: str):
        super().__init__(timeout=None)
        self.user = user
        self.nome = nome
        self.passaporte = passaporte

    async def verificar_permissao(self, interaction: discord.Interaction) -> bool:
        cargos = {r.name.lower() for r in interaction.user.roles} # CORRIGIDO: Usa set para comparação
        if not any(cargo in cargos for cargo in CARGOS_AUTORIZADOS): # CORRIGIDO: Compara com CARGOS_AUTORIZADOS
            await interaction.response.send_message(
                "❌ Você não tem permissão para aprovar/reprovar registros.", ephemeral=True
            )
            logger.warning(f"Tentativa de aprovação/reprovação de registro sem permissão por {interaction.user.display_name}.")
            return False
        return True

    @discord.ui.button(label="✔️ Aprovar", style=discord.ButtonStyle.success, custom_id="aprovar_registro")
    async def aprovar(self, interaction: discord.Interaction, button: Button):
        if not await self.verificar_permissao(interaction):
            return
        await self.finalizar_registro(interaction, aprovado=True)

    @discord.ui.button(label="❌ Reprovar", style=discord.ButtonStyle.danger, custom_id="reprovar_registro")
    async def reprovar(self, interaction: discord.Interaction, button: Button):
        if not await self.verificar_permissao(interaction):
            return
        await self.finalizar_registro(interaction, aprovado=False)

    async def finalizar_registro(self, interaction: discord.Interaction, aprovado: bool):
        try:
            try:
                await interaction.response.defer(ephemeral=True)
            except Exception:
                pass

            mensagem = interaction.message
            if mensagem and mensagem.embeds:
                embed = mensagem.embeds[0]
            else:
                embed = criar_embed(title="📋 Registro", description="Registro processado.", color=0x272727)

            if aprovado:
                status_texto = "✅ Aprovado"
                cor = 0x2ecc71
                try:
                    novo_nick = f"『 M 』{self.nome} | {self.passaporte}"
                    await self.user.edit(nick=novo_nick)
                    logger.info(f"Nick de {self.user.display_name} alterado para {novo_nick}.")
                except discord.Forbidden:
                    await interaction.followup.send("⚠️ Não consegui mudar o nick do usuário. Verifique minhas permissões.", ephemeral=True)
                    logger.warning(f"Sem permissão para mudar nick de {self.user.display_name} (ID: {self.user.id}).")
                except Exception as e:
                    await interaction.followup.send(f"❌ Erro ao mudar nick: {e}", ephemeral=True)
                    logger.error(f"Erro ao mudar nick de {self.user.display_name} (ID: {self.user.id}): {e}", exc_info=True)

                cargo_membro = discord.utils.get(interaction.guild.roles, name="Membro")
                if cargo_membro:
                    try:
                        await self.user.add_roles(cargo_membro)
                        logger.info(f"Cargo 'Membro' atribuído a {self.user.display_name}.")
                    except discord.Forbidden:
                        await interaction.followup.send("⚠️ Não consegui atribuir o cargo de Membro. Verifique minhas permissões.", ephemeral=True)
                        logger.warning(f"Sem permissão para atribuir cargo 'Membro' a {self.user.display_name} (ID: {self.user.id}).")
                    except Exception as e:
                        await interaction.followup.send(f"❌ Erro ao atribuir cargo: {e}", ephemeral=True)
                        logger.error(f"Erro ao atribuir cargo 'Membro' a {self.user.display_name} (ID: {self.user.id}): {e}", exc_info=True)

                categoria = interaction.guild.get_channel(CATEGORIA_FARM_ID)
                canal = None
                if categoria:
                    nome_canal = f"『M』{self.nome.lower().replace(' ', '-')}-{self.passaporte}"

                    overwrites = {
                        interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                        self.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                    }
                    # CORRIGIDO: Itera sobre CARGOS_AUTORIZADOS para configurar permissões
                    for cargo_nome in CARGOS_AUTORIZADOS:
                        cargo = discord.utils.get(interaction.guild.roles, name=cargo_nome)
                        if cargo:
                            overwrites[cargo] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

                    try:
                        canal = await categoria.create_text_channel(
                            name=nome_canal,
                            topic=f"Canal de farm do {self.user.name} | ID: {self.user.id}",
                            overwrites=overwrites
                        )
                        logger.info(f"Canal de farm '{nome_canal}' criado para {self.user.display_name}.")
                    except discord.Forbidden:
                        await interaction.followup.send("⚠️ Não tenho permissão para criar canais. Verifique minhas permissões.", ephemeral=True)
                        logger.warning(f"Sem permissão para criar canal de farm para {self.user.display_name} (ID: {self.user.id}).")
                    except Exception as e:
                        await interaction.followup.send(f"❌ Erro ao criar canal: {e}", ephemeral=True)
                        logger.error(f"Erro ao criar canal de farm para {self.user.display_name} (ID: {self.user.id}): {e}", exc_info=True)

                    if canal and isinstance(canal, discord.TextChannel) and canal.category_id == CATEGORIA_FARM_ID:
                        bot = interaction.client
                        from .farmview import FarmView # Importar FarmView aqui para evitar importação circular
                        if not hasattr(bot, "_suppress_recreate_farm"):
                            bot._suppress_recreate_farm = set()

                        embed_farm = criar_embed(
                            title="Entrega do Farm Semanal",
                            description="Clique no botão abaixo para entregar seu farm.",
                            color=0x272727
                        )
                        await limpar_e_enviar_view(
                            canal,
                            bot.user,
                            ID_MARCADOR,
                            embed_farm,
                            FarmView(),
                            bot._suppress_recreate_farm,
                            canal.id
                        )

            else:
                status_texto = "❌ Reprovado"
                cor = 0xe74c3c

            try:
                embed.color = cor
                embed.add_field(name="📌 Status", value=status_texto, inline=False)
                if mensagem:
                    await mensagem.edit(embed=embed, view=None)
                logger.info(f"Registro de {self.user.display_name} {status_texto.lower()} por {interaction.user.display_name}.")
            except Exception:
                logger.error("Erro ao editar mensagem de avaliação de registro.", exc_info=True)

            try:
                await interaction.followup.send(f"✅ Registro {status_texto.lower()}!", ephemeral=True)
            except Exception:
                pass

        except Exception:
            logger.error("Erro ao finalizar registro na AvaliacaoRegistroView.", exc_info=True)
            try:
                await interaction.followup.send("❌ Erro ao finalizar registro.", ephemeral=True)
            except Exception:
                pass

class RegistroView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Registrar Novo Membro",
        style=discord.ButtonStyle.success,
        custom_id="registrar",
    )
    async def open_modal(self, interaction: discord.Interaction, button: Button):
        try:
            await interaction.response.send_modal(RegistroModal())
        except Exception as e:
            logger.error(f"Erro ao abrir modal de registro: {e}", exc_info=True)
            try:
                await interaction.response.send_message(f"❌ Erro ao abrir registro: {e}", ephemeral=True)
            except Exception:
                pass