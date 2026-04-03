import discord
from discord.ext import commands, tasks
import asyncio
import logging

# imports locais
from config import TOKEN, CATEGORIA_FARM_ID, ID_MARCADOR, ID_MARCADOR_REGISTRO, ID_MARCADOR_PEDIDO, CANAL_REGISTRO_ID, CANAL_LOG_ID, CANAL_PEDIDO_ID
from views.farmview import FarmView # Importação corrigida
from views.registro import RegistroView # AvaliacaoRegistroView não deve ser importada aqui para registro global
from views.pedido import PedidoView # Importação corrigida
from utils.utils_prints import limpar_prints_expirados # Importação corrigida
from utils.utils_embeds import criar_embed # Importação corrigida
from utils.utils_discord import limpar_e_enviar_view # Importação da nova função utilitária

# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)

# Sets para suprimir recriação de botões durante operações
bot._suppress_recreate_farm     = set()
bot._suppress_recreate_registro = set()
bot._suppress_recreate_pedido   = set()

@tasks.loop(hours=24)
async def task_limpar_prints():
    try:
        removidos = limpar_prints_expirados()
        if removidos:
            logger.info(f"🧹 Limpeza de prints: {removidos} removido(s).")
    except Exception as e:
        logger.error(f"❌ Erro na limpeza de prints: {e}", exc_info=True)

@task_limpar_prints.before_loop
async def _before_task():
    await bot.wait_until_ready()

@bot.event
async def on_ready():
    logger.info(f"✅ Bot conectado como {bot.user}")

    try:
        # Registrar views persistentes
        bot.add_view(RegistroView())
        bot.add_view(PedidoView(bot))
        bot.add_view(FarmView())
        # AvaliacaoRegistroView é contextual e não deve ser registrada globalmente sem argumentos
        logger.info("✅ Views persistentes registradas globalmente.")

        # Enviar botão de registro
        canal_registro = bot.get_channel(CANAL_REGISTRO_ID)
        if canal_registro:
            embed_registro = criar_embed(
                title="📋 Registro de Novos Membros",
                description="Clique no botão abaixo para registrar-se no cartel.",
                color=0x272727,
            )
            await limpar_e_enviar_view(
                canal_registro,
                bot.user,
                ID_MARCADOR_REGISTRO,
                embed_registro,
                RegistroView(),
                bot._suppress_recreate_registro,
                canal_registro.id
            )
        else:
            logger.warning(f"❌ Canal de registro (ID: {CANAL_REGISTRO_ID}) não encontrado.")

        # Enviar botão de pedido
        canal_pedido = bot.get_channel(CANAL_PEDIDO_ID)
        if canal_pedido:
            embed_pedido = criar_embed(
                title="📦 Pedidos de Armas",
                description="Clique no botão abaixo para solicitar um orçamento.",
                color=0x272727,
            )
            await limpar_e_enviar_view(
                canal_pedido,
                bot.user,
                ID_MARCADOR_PEDIDO,
                embed_pedido,
                PedidoView(bot),
                bot._suppress_recreate_pedido,
                canal_pedido.id
            )
        else:
            logger.warning(f"❌ Canal de pedido (ID: {CANAL_PEDIDO_ID}) não encontrado.")

        # Enviar botões de farm nos canais de farm existentes
        for guild in bot.guilds:
            for canal in guild.text_channels:
                if canal.category_id == CATEGORIA_FARM_ID and canal.id != CANAL_PEDIDO_ID:
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

        synced = await bot.tree.sync()
        logger.info(f"🔁 Comandos de barra sincronizados: {len(synced)} comandos")

    except Exception as e:
        logger.error(f"❌ Erro no on_ready: {e}", exc_info=True)

    if not task_limpar_prints.is_running():
        task_limpar_prints.start()

@bot.event
async def on_guild_channel_create(canal):
    if isinstance(canal, discord.TextChannel) and canal.category_id == CATEGORIA_FARM_ID and canal.id != CANAL_PEDIDO_ID:
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

@bot.event
async def on_message_delete(message: discord.Message):
    if message.author != bot.user:
        return

    conteudo = (message.content or "").strip()

    if conteudo == ID_MARCADOR:
        if message.channel.id == CANAL_PEDIDO_ID:
            return
        embed_farm = criar_embed(
            title="Entrega do Farm Semanal",
            description="Clique no botão abaixo para entregar seu farm.",
            color=0x272727
        )
        await limpar_e_enviar_view(
            message.channel,
            bot.user,
            ID_MARCADOR,
            embed_farm,
            FarmView(),
            bot._suppress_recreate_farm,
            message.channel.id
        )

    elif conteudo == ID_MARCADOR_REGISTRO:
        canal_registro = bot.get_channel(CANAL_REGISTRO_ID)
        if canal_registro:
            embed_registro = criar_embed(
                title="📋 Registro de Novos Membros",
                description="Clique no botão abaixo para registrar-se no cartel.",
                color=0x272727,
            )
            await limpar_e_enviar_view(
                canal_registro,
                bot.user,
                ID_MARCADOR_REGISTRO,
                embed_registro,
                RegistroView(),
                bot._suppress_recreate_registro,
                canal_registro.id
            )

    elif conteudo == ID_MARCADOR_PEDIDO:
        canal_pedido = bot.get_channel(CANAL_PEDIDO_ID)
        if canal_pedido:
            embed_pedido = criar_embed(
                title="📦 Pedidos de Armas",
                description="Clique no botão abaixo para solicitar um orçamento.",
                color=0x272727,
            )
            await limpar_e_enviar_view(
                canal_pedido,
                bot.user,
                ID_MARCADOR_PEDIDO,
                embed_pedido,
                PedidoView(bot),
                bot._suppress_recreate_pedido,
                canal_pedido.id
            )

@bot.event
async def on_member_join(member):
    canal_registro = member.guild.get_channel(CANAL_REGISTRO_ID)
    if canal_registro:
        try:
            await member.send(
                f"👋 Seja bem-vindo ao servidor, {member.display_name}!\n"
                f"Por favor, vá até o canal <#{canal_registro.id}> e clique no botão para se registrar no cartel."
            )
        except discord.Forbidden:
            logger.warning(f"⚠️ Não foi possível enviar DM para {member.display_name}.")

@bot.event
async def on_member_remove(member):
    guild = member.guild
    canal_log = guild.get_channel(CANAL_LOG_ID)

    if canal_log:
        embed = criar_embed(
            title="🚪 Membro Saiu do Servidor",
            description=f"{member.mention} (`{member}`) saiu do servidor.",
            color=discord.Color.dark_gray(),
            footer_text=f"ID: {member.id}"
        )
        await canal_log.send(embed=embed)

    categoria = guild.get_channel(CATEGORIA_FARM_ID)
    if categoria:
        for canal in categoria.channels:
            if isinstance(canal, discord.TextChannel) and canal.topic:
                if f"ID: {member.id}" in canal.topic:
                    try:
                        await canal.delete(reason="Usuário saiu do servidor")
                        if canal_log:
                            await canal_log.send(f"🗑️ Canal `{canal.name}` foi deletado pois {member.mention} saiu.")
                    except discord.Forbidden:
                        if canal_log:
                            await canal_log.send(f"⚠️ Não consegui deletar o canal `{canal.name}` de {member.mention}.")
                    except Exception as e:
                        logger.error(f"❌ Erro ao deletar canal {canal.name} de {member.display_name}: {e}", exc_info=True)

async def main():
    async with bot:
        await bot.load_extension("cogs.farm_cog")
        await bot.load_extension("cogs.pedido_cog")
        await bot.load_extension("cogs.registrar_cog")
        await bot.load_extension("cogs.falar_cog")
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())