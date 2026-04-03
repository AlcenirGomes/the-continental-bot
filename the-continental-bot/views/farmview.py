import discord
import traceback
import logging
from discord.ui import Modal, TextInput, View, Button
from config import CARGO_ID, ID_MARCADOR, CATEGORIA_FARM_ID
from datetime import datetime
from utils_prints import registrar_print
from utils_embeds import criar_embed

logger = logging.getLogger(__name__)

class FarmModalParte1(Modal, title="Coleta de Materiais - Parte 1"):
    def __init__(self):
        super().__init__()
        self.cabo = TextInput(label="Cabo", required=True)
        self.clip = TextInput(label="Clip", required=True)
        self.culatra = TextInput(label="Culatra", required=True)
        self.ferrolho = TextInput(label="Ferrolho", required=True)
        self.slide = TextInput(label="Slide", required=True)

        self.add_item(self.cabo)
        self.add_item(self.clip)
        self.add_item(self.culatra)
        self.add_item(self.ferrolho)
        self.add_item(self.slide)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            valores_parte1 = {
                "Cabo": self.cabo.value.strip(),
                "Clip": self.clip.value.strip(),
                "Culatra": self.culatra.value.strip(),
                "Ferrolho": self.ferrolho.value.strip(),
                "Slide": self.slide.value.strip(),
            }

            view = ContinuarView(valores_parte1)
            await interaction.response.send_message(
                "✅ Parte 1 recebida! Clique no botão abaixo para informar o Titânio.",
                view=view,
                ephemeral=True
            )
        except Exception:
            traceback.print_exc()
            await interaction.response.send_message("❌ Erro ao processar Parte 1.", ephemeral=True)

class FarmModalParte2(Modal, title="Coleta de Materiais - Parte 2"):
    def __init__(self, valores_parte1: dict):
        super().__init__()
        self.valores_parte1 = valores_parte1
        self.titanio = TextInput(label="Titânio", required=True)
        self.add_item(self.titanio)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            try:
                valores = {k: int(v) for k, v in self.valores_parte1.items()}
                valores["Titânio"] = int(self.titanio.value.strip())
            except ValueError:
                await interaction.response.send_message("❌ Todos os valores devem ser inteiros.", ephemeral=True)
                return

            await interaction.response.send_message("✅ Valores recebidos! Agora envie um print (imagem).", ephemeral=True)

            def check_img(msg):
                return msg.author == interaction.user and msg.channel == interaction.channel and msg.attachments

            try:
                img_msg = await interaction.client.wait_for("message", check=check_img, timeout=120)
                anexo = img_msg.attachments[0]
                imagem_url = anexo.url

                data_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                nome_arquivo = f"{interaction.user.id}_{data_str}.png"

                registrar_print(user_id=interaction.user.id, cdn_url=imagem_url, nome_arquivo=nome_arquivo)

                arquivo = await anexo.to_file()

                try:
                    await img_msg.delete()
                except Exception:
                    pass

            except Exception:
                await interaction.followup.send("⏰ Tempo esgotado para enviar a imagem. Operação cancelada.", ephemeral=True)
                return

            apelido = interaction.user.nick or interaction.user.name
            if " | " in apelido:
                base_nome, passaporte = apelido.replace("『 M 』", "").split(" | ", 1)
                nome_canal_esperado = f"『M』{base_nome.lower().replace(' ', '-')}-{passaporte}"
            else:
                nome_canal_esperado = apelido.lower().replace(" ", "-")

            if not interaction.channel.topic or str(interaction.user.id) not in interaction.channel.topic:
                if interaction.channel.name != nome_canal_esperado:
                    try:
                        await interaction.channel.edit(name=nome_canal_esperado)
                    except discord.Forbidden:
                        await interaction.followup.send(
                            "⚠️ Não consegui renomear o canal. Permissões insuficientes.", ephemeral=True
                        )

            cargo = interaction.guild.get_role(CARGO_ID)
            embed = criar_embed(
                title="📦 Coleta de Materiais",
                description=f"{interaction.user.mention} enviou os seguintes dados:",
                color=0x272727,
                footer_text=f"Enviado por {interaction.user.name}",
            )
            for item, valor in valores.items():
                embed.add_field(name=item, value=str(valor), inline=True)

            embed.set_image(url=f"attachment://{arquivo.filename}")
            embed.add_field(name="📷 Print Enviado", value=f"[Clique aqui para visualizar]({imagem_url})", inline=False)

            mensagem_embed = await interaction.channel.send(
                content=f"{interaction.user.mention}",
                embed=embed,
                file=arquivo
            )

            from coleta import AvaliacaoView
            await mensagem_embed.edit(view=AvaliacaoView(mensagem_embed, embed, interaction.user))

            await interaction.channel.send("✅ Dados enviados com sucesso!", delete_after=10)

        except Exception:
            traceback.print_exc()
            await interaction.response.send_message("❌ Erro ao processar Parte 2.", ephemeral=True)

class ContinuarView(discord.ui.View):
    def __init__(self, valores_parte1: dict):
        super().__init__(timeout=60)
        self.valores_parte1 = valores_parte1

    @discord.ui.button(label="➡️ Continuar com Titânio", style=discord.ButtonStyle.primary)
    async def continuar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(FarmModalParte2(self.valores_parte1))

class FarmView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Abrir Formulário de Coleta",
        style=discord.ButtonStyle.primary,
        custom_id="botao_farm"
    )
    async def open_modal(self, interaction: discord.Interaction, button: Button):
        try:
            print(f"[DEBUG] open_modal chamado por {interaction.user} em {interaction.channel}")
            await interaction.response.send_modal(FarmModalParte1())

            try:
                await interaction.message.delete()
            except Exception:
                pass

        except Exception:
            traceback.print_exc()
            try:
                await interaction.response.send_message("❌ Erro ao abrir o formulário.", ephemeral=True)
            except Exception:
                pass

async def enviar_botao_se_necessario(canal: discord.TextChannel, bot_user):
    if canal.category_id != CATEGORIA_FARM_ID:
        return
    try:
        async for msg in canal.history(limit=50):
            if (
                msg.author == bot_user
                and msg.components
                and (msg.content or "").strip() == ID_MARCADOR
            ):
                print(f"⚠️ Botão já existe no canal {canal.name}, não vou duplicar.")
                return

        async for msg in canal.history(limit=50):
            if msg.author == bot_user and msg.components:
                try:
                    await msg.delete()
                except Exception:
                    pass

        embed = criar_embed(
            title="Entrega do Farm Semanal",
            description="Clique no botão abaixo para entregar seu farm.",
            color=0x272727
        )
        await canal.send(content=ID_MARCADOR, embed=embed, view=FarmView())
        print(f"✅ Botão de farm enviado automaticamente no canal {canal.name} (ID: {canal.id})")

    except discord.Forbidden:
        print(f"⚠️ Sem permissão para enviar mensagem em: {canal.name}")
    except Exception as e:
        print(f"❌ Erro ao enviar botão automático no canal {canal.name}: {e}")

async def enviar_botao_farm(canal: discord.TextChannel):
    try:
        async for msg in canal.history(limit=50):
            if (
                msg.author == canal.guild.me
                and msg.components
                and (msg.content or "").strip() == ID_MARCADOR
            ):
                print(f"⚠️ Botão já existe no canal {canal.name}, não vou duplicar.")
                return

        async for msg in canal.history(limit=50):
            if msg.author == canal.guild.me and msg.components:
                try:
                    await msg.delete()
                except Exception:
                    pass

        embed = criar_embed(
            title="Entrega do Farm Semanal",
            description="Clique no botão abaixo para entregar seu farm.",
            color=0x272727
        )
        await canal.send(content=ID_MARCADOR, embed=embed, view=FarmView())
        print(f"✅ Botão de farm enviado via registro no canal {canal.name} (ID: {canal.id})")

    except Exception as e:
        print(f"❌ Erro ao enviar botão via registro no canal {canal.name}: {e}")