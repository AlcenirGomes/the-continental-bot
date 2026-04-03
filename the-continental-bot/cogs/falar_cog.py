import discord
from discord.ext import commands
from discord import app_commands
import logging

from ..utils.utils_embeds import criar_embed
from ..config import CARGOS_AUTORIZADOS # CORRIGIDO: Importa CARGOS_AUTORIZADOS do config

logger = logging.getLogger(__name__)

# REMOVIDO: AUTHORIZED_ROLES foi movido para config.py

class EmbedModal(discord.ui.Modal, title="Criar Embed"):
    titulo = discord.ui.TextInput(label="Título", placeholder="Digite o título do embed", required=True)
    descricao = discord.ui.TextInput(label="Descrição", style=discord.TextStyle.paragraph, required=True)
    cor = discord.ui.TextInput(label="Cor (hex ou decimal)", placeholder="0x272727", required=False)
    footer = discord.ui.TextInput(label="Texto do Footer", placeholder="Opcional", required=False)
    imagem_url = discord.ui.TextInput(label="URL da Imagem", placeholder="https://exemplo.com/imagem.png", required=False)

    def __init__(self, original_interaction: discord.Interaction, bot_user: discord.User):
        super().__init__()
        self.original_interaction = original_interaction
        self.bot_user = bot_user

    async def on_submit(self, interaction: discord.Interaction):
        color_value = self.cor.value.strip()
        color = discord.Color.default()
        if color_value:
            try:
                color = (
                    discord.Color(int(color_value.strip("#"), 16))
                    if color_value.startswith("#")
                    else discord.Color(int(color_value))
                )
            except Exception as e:
                logger.warning(f"Cor inválida fornecida no EmbedModal: '{color_value}'. Usando cor padrão. Erro: {e}")
                pass

        embed = criar_embed(
            title=self.titulo.value,
            description=self.descricao.value,
            color=color,
            footer_text=self.footer.value.strip() if self.footer.value else "",
            image_url=self.imagem_url.value.strip() if self.imagem_url.value else None
        )

        try:
            await self.original_interaction.channel.send(embed=embed)
            await interaction.response.send_message("✅ Embed enviado com sucesso!", ephemeral=True)
            logger.info(f"Embed enviado por {self.original_interaction.user.display_name} no canal {self.original_interaction.channel.name}.")
        except discord.Forbidden:
            logger.warning(f"Sem permissão para enviar embed no canal {self.original_interaction.channel.name} (ID: {self.original_interaction.channel.id}).")
            await interaction.response.send_message("❌ Não tenho permissão para enviar mensagens neste canal.", ephemeral=True)
        except Exception as e:
            logger.error(f"Erro ao enviar embed no canal {self.original_interaction.channel.name}: {e}", exc_info=True)
            await interaction.response.send_message(f"❌ Erro ao enviar embed: {e}", ephemeral=True)

class DMModal(discord.ui.Modal, title="Enviar DM"):
    mensagem = discord.ui.TextInput(label="Mensagem", style=discord.TextStyle.paragraph, required=True)

    def __init__(self, target_member: discord.Member):
        super().__init__()
        self.target_member = target_member

    async def on_submit(self, interaction: discord.Interaction):
        if not self.target_member:
            await interaction.response.send_message("❌ Usuário inválido.", ephemeral=True)
            return
        try:
            await self.target_member.send(self.mensagem.value)
            await interaction.response.send_message(f"✅ Mensagem enviada para {self.target_member}.", ephemeral=True)
            logger.info(f"DM enviada por {interaction.user.display_name} para {self.target_member.display_name}.")
        except discord.Forbidden:
            await interaction.response.send_message("❌ O usuário bloqueou ou desativou DMs.", ephemeral=True)
            logger.warning(f"Não foi possível enviar DM para {self.target_member.display_name} (ID: {self.target_member.id}) - DMs bloqueadas.")
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao enviar DM: {e}", ephemeral=True)
            logger.error(f"Erro ao enviar DM para {self.target_member.display_name} (ID: {self.target_member.id}): {e}", exc_info=True)

class FalarCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="falar", description="Envie embed ou DM como bot")
    @app_commands.describe(
        metodo="Escolha entre embed no canal ou mensagem por DM",
        usuario="Escolha o usuário (necessário apenas para DM)"
    )
    @app_commands.choices(metodo=[
        app_commands.Choice(name="Embed no Canal", value="embed"),
        app_commands.Choice(name="Mensagem por DM", value="dm")
    ])
    async def falar(self, interaction: discord.Interaction,
                    metodo: app_commands.Choice[str],
                    usuario: str = None):

        membro = interaction.user
        cargos_usuario = {role.name.lower() for role in membro.roles}

        # CORRIGIDO: Usa CARGOS_AUTORIZADOS do config.py
        if not (cargos_usuario & set(CARGOS_AUTORIZADOS)):
            await interaction.response.send_message("❌ Você não tem permissão para usar este comando.", ephemeral=True)
            logger.warning(f"Comando /falar: Tentativa de uso sem permissão por {interaction.user.display_name}.")
            return

        if metodo.value == "embed":
            await interaction.response.send_modal(EmbedModal(interaction, self.bot.user))
        elif metodo.value == "dm":
            if not usuario:
                await interaction.response.send_message("❌ Você precisa fornecer um usuário para enviar DM.", ephemeral=True)
                return
            target = None
            # Tenta encontrar por nome
            if interaction.guild:
                target = discord.utils.get(interaction.guild.members, name=usuario)

            # Se não encontrou por nome, tenta por ID
            if not target:
                try:
                    target = await self.bot.fetch_user(int(usuario))
                except (ValueError, discord.NotFound):
                    pass # Não encontrou por ID, target permanece None

            if not target:
                await interaction.response.send_message("❌ Usuário não encontrado. Tente usar o ID do usuário.", ephemeral=True)
                logger.warning(f"Comando /falar dm: Usuário '{usuario}' não encontrado.")
                return
            await interaction.response.send_modal(DMModal(target))

async def setup(bot: commands.Bot):
    await bot.add_cog(FalarCog(bot))