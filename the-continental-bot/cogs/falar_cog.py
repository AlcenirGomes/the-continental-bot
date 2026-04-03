import discord
from discord.ext import commands
from discord import app_commands
from utils_embeds import criar_embed

AUTHORIZED_ROLES = {"administrador", "01", "02", "03", "gerente"}

class EmbedModal(discord.ui.Modal, title="Criar Embed"):
    titulo = discord.ui.TextInput(label="Título", placeholder="Digite o título do embed", required=True)
    descricao = discord.ui.TextInput(label="Descrição", style=discord.TextStyle.paragraph, required=True)
    cor = discord.ui.TextInput(label="Cor (hex ou decimal)", placeholder="0x272727", required=False)
    footer = discord.ui.TextInput(label="Texto do Footer", placeholder="Opcional", required=False)
    imagem_url = discord.ui.TextInput(label="URL da Imagem", placeholder="https://exemplo.com/imagem.png", required=False)

    def __init__(self, original_interaction: discord.Interaction):
        super().__init__()
        self.original_interaction = original_interaction

    async def on_submit(self, interaction: discord.Interaction):
        color_value = self.cor.value.strip()
        color = discord.Color.default()
        if color_value:
            try:
                color = (
                    discord.Color(int(color_value.strip("#"), 16))
                    if color_value.startswith("#")")
                    else discord.Color(int(color_value))
                )
            except Exception:
                pass

        embed = criar_embed(
            title=self.titulo.value,
            description=self.descricao.value,
            color=color,
            footer_text=self.footer.value.strip() if self.footer.value else "",
            image_url=self.imagem_url.value.strip() if self.imagem_url.value else None
        )

        async for msg in self.original_interaction.channel.history(limit=50):
            if msg.author == interaction.client.user and msg.embeds:
                try:
                    await msg.delete()
                except Exception:
                    pass

        await interaction.response.send_message("✅ Embed enviado com sucesso!", ephemeral=True)
        await self.original_interaction.followup.send(embed=embed)

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
        except discord.Forbidden:
            await interaction.response.send_message("❌ O usuário bloqueou ou desativou DMs.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erro ao enviar DM: {e}", ephemeral=True)

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
        cargos = {role.name.lower() for role in membro.roles}

        if not (cargos & AUTHORIZED_ROLES):
            await interaction.response.send_message("❌ Você não tem permissão para usar este comando.", ephemeral=True)
            return

        if metodo.value == "embed":
            await interaction.response.send_modal(EmbedModal(interaction))
        elif metodo.value == "dm":
            if not usuario:
                await interaction.response.send_message("❌ Você precisa fornecer um usuário para enviar DM.", ephemeral=True)
                return
            target = discord.utils.get(interaction.guild.members, name=usuario)
            if not target:
                await interaction.response.send_message("❌ Usuário não encontrado.", ephemeral=True)
                return
            await interaction.response.send_modal(DMModal(target))

async def setup(bot: commands.Bot):
    await bot.add_cog(FalarCog(bot))