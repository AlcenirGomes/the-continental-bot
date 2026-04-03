import discord
from discord.ext import commands, tasks
import asyncio

# imports locais
from config import TOKEN, CATEGORIA_FARM_ID, ID_MARCADOR, ID_MARCADOR_REGISTRO, ID_MARCADOR_PEDIDO, CANAL_REGISTRO_ID, CANAL_LOG_ID, CANAL_PEDIDO_ID
from farmview import FarmView, enviar_botao_se_necessario
from registro import enviar_botao_registro, RegistroView, verificar_registro_apagado, AvaliacaoRegistroView
from pedido import PedidoView
from utils_prints import limpar_prints_expirados
from utils_embeds import criar_embed

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)

bot._suppress_recreate_farm     = set()
bot._suppress_recreate_registro = set()
bot._suppress_recreate_pedido   = set()


@tasks.loop(hours=24)
async def task_limpar_prints():
    try:
        removidos = limpar_prints_expirados()
        if removidos:
            print(f"🧹 Limpeza de prints: {removidos} removido(s).")
    except Exception as e:
        print(f"❌ Erro na limpeza de prints: {e}")


@task_limpar_prints.before_loop
async def _before_task():
    await bot.wait_until_ready()


@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")

    try:
        bot.add_view(RegistroView())
        bot.add_view(PedidoView(bot))
        bot.add_view(FarmView())
        bot.add_view(AvaliacaoRegistroView(None, "", ""))
        print("✅ Views registradas globalmente")

        await enviar_botao_registro(bot)

        canal_pedido = bot.get_channel(CANAL_PEDIDO_ID)
        if canal_pedido:
            ja_existe = False
            async for msg in canal_pedido.history(limit=50):
                if (
                    msg.author == bot.user
                    and msg.components
                    and (msg.content or "").strip() == ID_MARCADOR_PEDIDO # Usar ID_MARCADOR_PEDIDO
                ):
                    ja_existe = True
                    break
            if not ja_existe:
                bot._suppress_recreate_pedido.add(canal_pedido.id)
                try:
                    async for msg in canal_pedido.history(limit=50):
                        if msg.author == bot.user and msg.components:
                            try:
                                await msg.delete()
                            except Exception:
                                pass
                    await canal_pedido.send(
                        content=ID_MARCADOR_PEDIDO, # Usar ID_MARCADOR_PEDIDO
                        embed=criar_embed(
                            title="📦 Pedidos de Armas",
                            description="Clique no botão abaixo para solicitar um orçamento.",
                            color=0x272727,
                        ),
                        view=PedidoView(bot)
                    )
                    print("✅ Botão de pedido criado.")
                finally:
                    bot._suppress_recreate_pedido.discard(canal_pedido.id)

        for guild in bot.guilds:
            for canal in guild.text_channels:
                if canal.category_id == CATEGORIA_FARM_ID and canal.id != CANAL_PEDIDO_ID:
                    ja_existe = False
                    async for msg in canal.history(limit=50):
                        if (
                            msg.author == bot.user
                            and msg.components
                            and (msg.content or "").strip() == ID_MARCADOR # Usar ID_MARCADOR
                        ):
                            ja_existe = True
                            break
                    if not ja_existe:
                        bot._suppress_recreate_farm.add(canal.id)
                        try:
                            await enviar_botao_se_necessario(canal, bot.user)
                        finally:
                            bot._suppress_recreate_farm.discard(canal.id)

        synced = await bot.tree.sync()
        print(f"🔁 Comandos de barra sincronizados: {len(synced)} comandos")

    except Exception as e:
        print(f"❌ Erro no on_ready: {e}")

    if not task_limpar_prints.is_running():
        task_limpar_prints.start()


@bot.event
async def on_guild_channel_create(canal):
    if isinstance(canal, discord.TextChannel) and canal.category_id == CATEGORIA_FARM_ID and canal.id != CANAL_PEDIDO_ID:
        if canal.id in getattr(bot, "_suppress_recreate_farm", set()):
            return
        bot._suppress_recreate_farm.add(canal.id)
        try:
            await enviar_botao_se_necessario(canal, bot.user)
        finally:
            bot._suppress_recreate_farm.discard(canal.id)


@bot.event
async def on_message_delete(message: discord.Message):
    if message.author != bot.user:
        return

    conteudo = (message.content or "").strip()

    if conteudo == ID_MARCADOR:
        if message.channel.id in getattr(bot, "_suppress_recreate_farm", set()):
            return
        if message.channel.id == CANAL_PEDIDO_ID:
            return
        bot._suppress_recreate_farm.add(message.channel.id)
        try:
            await enviar_botao_se_necessario(message.channel, bot.user)
        finally:
            bot._suppress_recreate_farm.discard(message.channel.id)

    elif conteudo == ID_MARCADOR_REGISTRO:
        if message.channel.id in getattr(bot, "_suppress_recreate_registro", set()):
            return
        await enviar_botao_registro(bot)

    elif conteudo == ID_MARCADOR_PEDIDO:
        if message.channel.id in getattr(bot, "_suppress_recreate_pedido", set()):
            return
        canal = bot.get_channel(CANAL_PEDIDO_ID)
        if canal:
            bot._suppress_recreate_pedido.add(canal.id)
            try:
                async for msg in canal.history(limit=50):
                    if msg.author == bot.user and msg.components:
                        try:
                            await msg.delete()
                        except Exception:
                            pass
                await canal.send(
                    content=ID_MARCADOR_PEDIDO,
                    embed=criar_embed(
                        title="📦 Pedidos de Armas",
                        description="Clique no botão abaixo para solicitar um orçamento.",
                        color=0x272727,
                    ),
                    view=PedidoView(bot)
                )
            finally:
                bot._suppress_recreate_pedido.discard(canal.id)


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
            print(f"⚠️ Não foi possível enviar DM para {member.display_name}.")


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


async def main():
    async with bot:
        await bot.load_extension("farm_cog")
        await bot.load_extension("pedido_cog")
        await bot.load_extension("registrar_cog")
        await bot.load_extension("falar_cog") # Certifique-se de que este cog existe
        await bot.start(TOKEN)


asyncio.run(main())