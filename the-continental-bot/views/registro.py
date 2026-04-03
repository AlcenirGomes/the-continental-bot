import discord
from discord.ui import View, Button
import traceback

from config import CATEGORIA_FARM_ID, CARGOS_AUTORIZADOS, ID_MARCADOR_REGISTRO, CANAL_REGISTRO_ID, CANAL_APROVACAO_ID, ID_MARCADOR
from farmview import enviar_botao_se_necessario # Importar aqui
from utils_embeds import criar_embed

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
            else:
                await interaction.response.send_message("❌ Canal de aprovação não encontrado.", ephemeral=True)

        except Exception:
            traceback.print_exc()
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
        cargos = [r.name.lower() for r in interaction.user.roles]
        if not any(cargo in CARGOS_AUTORIZADOS for cargo in cargos):
            await interaction.response.send_message(
                "❌ Você não tem permissão para aprovar/reprovar registros.", ephemeral=True
            )
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
                except discord.Forbidden:
                    await interaction.followup.send("⚠️ Não consegui mudar o nick do usuário.", ephemeral=True)
                except Exception as e:
                    await interaction.followup.send(f"❌ Erro ao mudar nick: {e}", ephemeral=True)

                cargo_membro = discord.utils.get(interaction.guild.roles, name="Membro")
                if cargo_membro:
                    try:
                        await self.user.add_roles(cargo_membro)
                    except discord.Forbidden:
                        await interaction.followup.send("⚠️ Não consegui atribuir o cargo de Membro.", ephemeral=True)
                    except Exception as e:
                        await interaction.followup.send(f"❌ Erro ao atribuir cargo: {e}", ephemeral=True)

                categoria = interaction.guild.get_channel(CATEGORIA_FARM_ID)
                canal = None
                if categoria:
                    nome_canal = f"『M』{self.nome.lower().replace(' ', '-')}-{self.passaporte}"

                    overwrites = {
                        interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                        self.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                    }
                    for cargo_nome in ["01", "02", "03", "gerente"]:
                        cargo = discord.utils.get(interaction.guild.roles, name=cargo_nome)
                        if cargo:
                            overwrites[cargo] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

                    try:
                        canal = await categoria.create_text_channel(
                            name=nome_canal,
                            topic=f"Canal de farm do {self.user.name} | ID: {self.user.id}",
                            overwrites=overwrites
                        )
                    except discord.Forbidden:
                        await interaction.followup.send("⚠️ Não tenho permissão para criar canais.", ephemeral=True)
                    except Exception as e:
                        await interaction.followup.send(f"❌ Erro ao criar canal: {e}", ephemeral=True)

                    if canal and isinstance(canal, discord.TextChannel) and canal.category_id == CATEGORIA_FARM_ID:
                        bot = interaction.client
                        if not hasattr(bot, "_suppress_recreate_farm"):
                            bot._suppress_recreate_farm = set()
                        bot._suppress_recreate_farm.add(canal.id)
                        try:
                            await enviar_botao_se_necessario(canal, bot.user)
                        except Exception as e:
                            await interaction.followup.send(f"❌ Erro ao enviar botão de farm: {e}", ephemeral=True)
                        finally:
                            bot._suppress_recreate_farm.discard(canal.id)

            else:
                status_texto = "❌ Reprovado"
                cor = 0xe74c3c

            try:
                embed.color = cor
                embed.add_field(name="📌 Status", value=status_texto, inline=False)
                if mensagem:
                    await mensagem.edit(embed=embed, view=None)
            except Exception:
                traceback.print_exc()

            try:
                await interaction.followup.send(f"✅ Registro {status_texto.lower()}!", ephemeral=True)
            except Exception:
                pass

        except Exception:
            traceback.print_exc()
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
            traceback.print_exc()
            try:
                await interaction.response.send_message(f"❌ Erro ao abrir registro: {e}", ephemeral=True)
            except Exception:
                pass

async def enviar_botao_registro(bot):
    canal = bot.get_channel(CANAL_REGISTRO_ID)
    if canal:
        if not hasattr(bot, "_suppress_recreate_registro"):
            bot._suppress_recreate_registro = set()
        bot._suppress_recreate_registro.add(canal.id)
        try:
            async for msg in canal.history(limit=50):
                if msg.author == bot.user and msg.components:
                    try:
                        await msg.delete()
                    except Exception:
                        pass

            embed = criar_embed(
                title="📋 Registro de Novos Membros",
                description="Clique no botão abaixo para registrar-se no cartel.",
                color=0x272727,
            )
            await canal.send(content=ID_MARCADOR_REGISTRO, embed=embed, view=RegistroView()) # Usar ID_MARCADOR_REGISTRO
            print("✅ Botão de registro enviado no canal de registro.")
        finally:
            try:
                bot._suppress_recreate_registro.discard(canal.id)
            except Exception:
                pass

async def verificar_registro_apagado(message, bot):
    if message.author == bot.user and message.components:
        if message.channel.id in getattr(bot, "_suppress_recreate_registro", set()):
            return

    if message.author == bot.user and message.components and (message.content or "").strip() == ID_MARCADOR_REGISTRO: # Usar ID_MARCADOR_REGISTRO
        if message.channel.id != CANAL_REGISTRO_ID:
            return
        canal = message.channel
        print("⚠️ Mensagem de registro apagada, recriando botão...")
        await enviar_botao_registro(bot)