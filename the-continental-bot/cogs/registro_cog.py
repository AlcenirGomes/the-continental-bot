import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

async def limpar_e_enviar_view(
    canal: discord.TextChannel,
    bot_user: discord.User,
    content: str,
    embed: discord.Embed,
    view: discord.ui.View,
    suppress_set: set = None,
    channel_id_to_suppress: int = None
):
    """
    Limpa mensagens antigas do bot com componentes em um canal e envia uma nova view.

    Args:
        canal (discord.TextChannel): O canal onde a operação será realizada.
        bot_user (discord.User): O objeto User do bot.
        content (str): O conteúdo da mensagem a ser enviada (geralmente um marcador).
        embed (discord.Embed): O embed a ser enviado com a view.
        view (discord.ui.View): A view (botões) a ser enviada.
        suppress_set (set, optional): Um set para gerenciar a supressão de recriação. Defaults to None.
        channel_id_to_suppress (int, optional): O ID do canal a ser adicionado/removido do suppress_set. Defaults to None.
    """
    if suppress_set is not None and channel_id_to_suppress is not None:
        if channel_id_to_suppress in suppress_set:
            logger.info(f"Operação de limpeza e envio suprimida para o canal {canal.name} (ID: {canal.id}).")
            return

        suppress_set.add(channel_id_to_suppress)

    try:
        # Limpar mensagens antigas do bot com componentes
        async for msg in canal.history(limit=50):
            if msg.author == bot_user and msg.components:
                try:
                    await msg.delete()
                except discord.Forbidden:
                    logger.warning(f"Sem permissão para deletar mensagem em {canal.name} (ID: {canal.id}).")
                except Exception as e:
                    logger.error(f"Erro ao deletar mensagem em {canal.name} (ID: {canal.id}): {e}", exc_info=True)

        # Enviar a nova mensagem com a view
        await canal.send(content=content, embed=embed, view=view)
        logger.info(f"Botão enviado/recriado no canal {canal.name} (ID: {canal.id}).")

    except discord.Forbidden:
        logger.warning(f"Sem permissão para enviar mensagem em {canal.name} (ID: {canal.id}).")
    except Exception as e:
        logger.error(f"Erro ao enviar botão no canal {canal.name} (ID: {canal.id}): {e}", exc_info=True)
    finally:
        if suppress_set is not None and channel_id_to_suppress is not None:
            suppress_set.discard(channel_id_to_suppress)