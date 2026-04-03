import discord
from discord.ext import commands, tasks
import asyncio
import logging
import os # Importar os para ENVIRONMENT

# imports locais
from config import (
    TOKEN, CATEGORIA_FARM_ID, ID_MARCADOR, ID_MARCADOR_REGISTRO, ID_MARCADOR_PEDIDO,
    CANAL_REGISTRO_ID, CANAL_LOG_ID, CANAL_PEDIDO_ID, PREFIX, ENVIRONMENT # Adicionado PREFIX e ENVIRONMENT
)
from views.farmview import FarmView
from views.registro import RegistroView
from views.pedido import PedidoView
from utils.utils_prints import limpar_prints_expirados
from utils.utils_embeds import criar_embed
from utils.utils_discord import limpar_e_enviar_view

# --- Configuração de Logging ---
# Configura o logging para exibir mensagens no console e em um arquivo
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s', # Adicionado %(name)s para identificar o módulo
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"), # Salva logs em um arquivo
        logging.StreamHandler()         # Exibe logs no console
    ]
)
logger = logging.getLogger(__name__)

# --- Configuração de Intents ---
# Defina as intents que seu bot realmente precisa.
# Ative-as também no Portal do Desenvolvedor do Discord.
intents = discord.Intents.default()
intents.message_content = True # Necessário para ler o conteúdo das mensagens (comandos de prefixo)
intents.members = True         # Necessário para acessar informações de membros (ex: ctx.author.name)
intents.guilds = True          # Necessário para acessar informações de servidores (guilds)
# Se você usa eventos como on_member_join, on_member_remove, etc., pode precisar de intents.presences ou outras.

# --- Inicialização do Bot ---
bot = commands.Bot(command_prefix=commands.when_mentioned_or(PREFIX), intents=intents) # CORRIGIDO: Prefixo e intents

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
    logger.info(f"✅ Bot conectado como {bot.user} (ID: {bot.user.id})")
    logger.info(f"Ambiente: {ENVIRONMENT}")

    try:
        # Registrar views persistentes
        bot.add_view(RegistroView())
        bot.add_view(PedidoView(bot))
        bot.add_view(FarmView())
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
                # CORRIGIDO: Verifica se o canal está na categoria de farm E não é o canal de pedido
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

        # CORRIGIDO: Sincronização de comandos de árvore condicional
        if ENVIRONMENT == "development":
            try:
                synced = await bot.tree.sync()
                logger.info(f"🔁 Comandos de barra sincronizados: {len(synced)} comandos")
            except Exception as e:
                logger.error(f"❌ Erro ao sincronizar comandos de barra: {e}", exc_info=True)
        else:
            logger.info("Sincronização de comandos de barra ignorada em ambiente de produção.")

    except Exception as e:
        logger.error(f"❌ Erro no on_ready: {e}", exc_info=True)

    if not task_limpar_prints.is_running():
        task_limpar_prints.start()

# --- Manipulador Global de Erros de Comandos ---
@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    """Manipulador global de erros para comandos de prefixo e híbridos."""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Comando não encontrado. Verifique a digitação ou use `!help`.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Argumento faltando: `{error.param}`. Por favor, forneça todos os argumentos necessários.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("Você não tem permissão para usar este comando.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(f"Eu não tenho permissão para executar esta ação. Preciso da permissão: `{', '.join(error.missing_permissions)}`.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"Este comando está em cooldown. Tente novamente em {error.retry_after:.2f} segundos.")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("Este comando não pode ser usado em mensagens privadas.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"Argumento inválido: {error}. Verifique o tipo de dado esperado.")
    else:
        logger.error(f"Erro inesperado no comando '{ctx.command}' por {ctx.author} ({ctx.author.id}): {error}", exc_info=True)
        await ctx.send("Ocorreu um erro inesperado ao executar o comando. O desenvolvedor foi notificado.")

# --- Comandos de Administração (Exemplo) ---
@bot.command(name="sync", description="Sincroniza os comandos de barra globalmente (apenas para o dono do bot).")
@commands.is_owner() # Garante que apenas o dono do bot pode usar este comando
async def sync_commands(ctx: commands.Context):
    """Sincroniza os comandos de barra globalmente."""
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"Sincronizados {len(synced)} comandos de barra globalmente.")
        logger.info(f"Comandos de barra sincronizados por {ctx.author.name} ({ctx.author.id}).")
    except Exception as e:
        await ctx.send(f"Falha ao sincronizar comandos de barra: {e}")
        logger.error(f"Falha ao sincronizar comandos de barra: {e}", exc_info=True)

@bot.command(name="reload", description="Recarrega um cog específico (apenas para o dono do bot).")
@commands.is_owner()
async def reload_cog(ctx: commands.Context, cog_name: str):
    """Recarrega um cog específico."""
    try:
        await bot.reload_extension(f'cogs.{cog_name}')
        await ctx.send(f"Cog `{cog_name}` recarregado com sucesso.")
        logger.info(f"Cog '{cog_name}' recarregado por {ctx.author.name}.")
    except commands.ExtensionNotLoaded:
        await ctx.send(f"O cog `{cog_name}` não está carregado.")
    except commands.ExtensionNotFound:
        await ctx.send(f"O cog `{cog_name}` não foi encontrado.")
    except Exception as e:
        await ctx.send(f"Falha ao recarregar cog `{cog_name}`: {e}")
        logger.error(f"Falha ao recarregar cog '{cog_name}': {e}", exc_info=True)

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
        if message.channel.id == CANAL_PEDIDO_ID: # Não recriar botão de farm no canal de pedido
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
            logger.warning(f"⚠️ Não foi possível enviar DM para {member.display_name} (ID: {member.id}).")

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

# --- Função Principal para Iniciar o Bot ---
async def main():
    async with bot:
        # CORRIGIDO: Carregamento de cogs dinâmico
        await load_cogs()
        await bot.start(TOKEN)

# CORRIGIDO: Função para carregar cogs dinamicamente
async def load_cogs():
    """Carrega todos os cogs da pasta 'cogs'."""
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            try:
                # CORRIGIDO: O cog 'registrar_cog' deve ser 'registro_cog'
                cog_name = filename[:-3]
                if cog_name == "registrar_cog": # Se você tem um arquivo chamado registrar_cog.py
                    cog_name = "registro_cog" # Mude para o nome correto do módulo

                await bot.load_extension(f'cogs.{cog_name}')
                logger.info(f'Cog {cog_name} carregado com sucesso.')
            except Exception as e:
                logger.error(f'Falha ao carregar cog {filename[:-3]}: {e}', exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())