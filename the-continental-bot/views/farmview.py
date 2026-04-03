import discord
import traceback
import logging
from discord.ui import Modal, TextInput, View, Button
from datetime import datetime, timedelta # Importado timedelta para cooldown
import asyncio

from ..config import CARGO_ID, ID_MARCADOR, CATEGORIA_FARM_ID # Importação relativa corrigida
from ..utils.utils_prints import registrar_print
from ..utils.utils_embeds import criar_embed
from ..utils.utils_discord import limpar_e_enviar_view
# from .coleta import AvaliacaoView # AvaliacaoView é importada dentro de on_submit para evitar importação circular

logger = logging.getLogger(__name__)

# --- Cooldown de Farm (sem DB, usando um dicionário em memória) ---
# ATENÇÃO: Este dicionário será resetado toda vez que o bot for reiniciado.
# Para persistência, um banco de dados seria necessário.
user_farm_cooldowns = {}
FARM_COOLDOWN_SECONDS = 3600 # 1 hora de cooldown

class FarmModalParte1(Modal, title="Coleta de Materiais - Parte 1"):
    def __init__(self):
        super().__init__()
        self.cabo = TextInput(label="Cabo", required=True)
        self.clip = TextInput(label="Clipper", required=True)
        self.culatra = TextInput(label="Culatra", required=True)
        self.ferrolho = TextInput(label="Ferrolho", required=True)
        self.slide = TextInput(label="Slide", required=True)

        self.add_item(self.cabo)
        self.add_item(self.clip)
        self.add_item(self.culatra)
        self.add_item(self.ferrolho)
        self.add_item(self.slide)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        now = datetime.now()

        # Verifica o cooldown
        if user_id in user_farm_cooldowns:
            last_farm_time = user_farm_cooldowns[user_id]
            time_since_last_farm = now - last_farm_time
            if time_since_last_farm.total_seconds() < FARM_COOLDOWN_SECONDS:
                remaining_time = timedelta(seconds=FARM_COOLDOWN_SECONDS) - time_since_last_farm
                hours, remainder = divmod(int(remaining_time.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                await interaction.response.send_message(
                    f"⏰ {interaction.user.mention}, você precisa esperar mais {hours}h {minutes}m {seconds}s para farmar novamente.",
                    ephemeral=True
                )
                logger.info(f"FarmModalParte1: Cooldown ativo para {interaction.user.display_name}.")
                return

        try:
            valores_parte1 = {
                "Cabo": self.cabo.value.strip(),
                "Clipper": self.clip.value.strip(),
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
            logger.info(f"FarmModalParte1 submetido por {interaction.user.display_name}.")
        except Exception:
            logger.error("Erro ao processar Parte 1 no FarmModalParte1.", exc_info=True)
            await interaction.response.send_message("❌ Erro ao processar Parte 1.", ephemeral=True)

class FarmModalParte2(Modal, title="Coleta de Materiais - Parte 2"):
    def __init__(self, valores_parte1: dict):
        super().__init__()
        self.valores_parte1 = valores_parte1
        self.titanio = TextInput(label="Titânio", required=True)
        self.add_item(self.titanio)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        try:
            try:
                valores = {k: int(v) for k, v in self.valores_parte1.items()}
                valores["Titânio"] = int(self.titanio.value.strip())
            except ValueError:
                await interaction.response.send_message("❌ Todos os valores devem ser números inteiros.", ephemeral=True)
                logger.warning(f"Valores não inteiros fornecidos por {interaction.user.display_name} no FarmModalParte2.")
                return

            await interaction.response.send_message("✅ Valores recebidos! Agora envie um print (imagem).", ephemeral=True)
            logger.info(f"FarmModalParte2 submetido por {interaction.user.display_name}. Aguardando imagem.")

            def check_img(msg):
                return msg.author == interaction.user and msg.channel == interaction.channel and msg.attachments

            try:
                img_msg = await interaction.client.wait_for("message", check=check_img, timeout=120)
                anexo = img_msg.attachments[0]
                imagem_url = anexo.url

                data_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                nome_arquivo = f"{interaction.user.id}_{data_str}.png"

                registrar_print(user_id=interaction.user.id, cdn_url=imagem_url, nome_arquivo=nome_arquivo)
                logger.info(f"Print registrado para {interaction.user.display_name}: {nome_arquivo}")

                arquivo = await anexo.to_file()

                try:
                    await img_msg.delete()
                except discord.Forbidden:
                    logger.warning(f"Sem permissão para deletar mensagem de imagem de {interaction.user.display_name}.")
                except Exception:
                    logger.warning(f"Não foi possível deletar mensagem de imagem de {interaction.user.display_name}.")
                    pass

            except asyncio.TimeoutError:
                await interaction.followup.send("⏰ Tempo esgotado para enviar a imagem. Operação cancelada.", ephemeral=True)
                logger.info(f"Tempo esgotado para imagem de {interaction.user.display_name}.")
                return
            except Exception as e:
                logger.error(f"Erro ao receber imagem de {interaction.user.display_name}: {e}", exc_info=True)
                await interaction.followup.send("❌ Erro ao receber a imagem. Operação cancelada.", ephemeral=True)
                return

            apelido = interaction.user.nick or interaction.user.name
            if " | " in apelido:
                base_nome, passaporte = apelido.replace("『 M 』", "").split(" | ", 1)
                nome_canal_esperado = f"『M』{base_nome.lower().replace(' ', '-')}-{passaporte}"
            else:
                nome_canal_esperado = apelido.lower().replace(" ", "-")

            # CORRIGIDO: Verifica se o canal é um TextChannel antes de acessar .topic
            if isinstance(interaction.channel, discord.TextChannel) and (not interaction.channel.topic or str(interaction.user.id) not in interaction.channel.topic):
                if interaction.channel.name != nome_canal_esperado:
                    try:
                        await interaction.channel.edit(name=nome_canal_esperado)
                        logger.info(f"Canal {interaction.channel.name} renomeado para {nome_canal_esperado}.")
                    except discord.Forbidden:
                        await interaction.followup.send(
                            "⚠️ Não consegui renomear o canal. Permissões insuficientes.", ephemeral=True
                        )
                        logger.warning(f"Sem permissão para renomear canal {interaction.channel.name}.")
                    except Exception as e:
                        logger.error(f"Erro ao renomear canal {interaction.channel.name}: {e}", exc_info=True)
                        await interaction.followup.send(f"❌ Erro ao renomear canal: {e}", ephemeral=True)

            embed = criar_embed(
                title="📦 Coleta de Materiais",
                description=f"{interaction.user.mention} enviou os seguintes dados:",
                color=0x272727,
                footer_text=f"Enviado por {interaction.user.name}",
            )
            for item, valor in valores.items():
                embed.add_field(name=item, value=str(valor), inline=True)

            embed.set_image(url=imagem_url)
            embed.add_field(name="📷 Print Enviado", value=f"[Clique aqui para visualizar]({imagem_url})", inline=False)

            mensagem_embed = await interaction.channel.send(
                content=f"{interaction.user.mention}",
                embed=embed,
                file=arquivo
            )

            from .coleta import AvaliacaoView # Importar AvaliacaoView aqui para evitar importação circular
            await mensagem_embed.edit(view=AvaliacaoView(mensagem_embed, embed, interaction.user))
            logger.info(f"Coleta de {interaction.user.display_name} enviada para avaliação.")

            await interaction.channel.send("✅ Dados enviados com sucesso!", delete_after=10)

            # Define o cooldown após o envio bem-sucedido
            user_farm_cooldowns[user_id] = datetime.now()

        except Exception:
            logger.error("Erro ao processar Parte 2 no FarmModalParte2.", exc_info=True)
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
            logger.debug(f"open_modal chamado por {interaction.user} em {interaction.channel}")
            await interaction.response.send_modal(FarmModalParte1())

            try:
                if interaction.message:
                    await interaction.message.delete()
            except discord.Forbidden:
                logger.warning(f"Sem permissão para deletar mensagem de interação em {interaction.channel.name} (ID: {interaction.channel.id}).")
            except Exception:
                pass

        except Exception:
            logger.error("Erro ao abrir o formulário de farm.", exc_info=True)
            try:
                await interaction.response.send_message("❌ Erro ao abrir o formulário.", ephemeral=True)
            except Exception:
                pass