import io
import os
import logging
import asyncio
import aiohttp
import cloudinary
import cloudinary.uploader
from functools import partial
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# CORRIGIDO: Adicionado verificação para as variáveis de ambiente da Cloudinary
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY    = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

if not all([CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET]):
    logger.error("❌ Variáveis de ambiente da Cloudinary não configuradas. O upload de imagens pode falhar.")
    # Você pode optar por levantar um erro aqui para impedir o bot de iniciar se as chaves forem críticas
    # raise ValueError("Credenciais da Cloudinary ausentes. Verifique seu arquivo .env.")
else:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True,
    )
    logger.info("✅ Configuração da Cloudinary carregada.")


async def baixar_em_memoria(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
                logger.warning(f"Falha ao baixar imagem da URL {url}. Status: {resp.status}")
                return None
    except Exception as e:
        logger.error(f"Erro ao baixar imagem da URL {url}: {e}", exc_info=True)
        return None

async def fazer_upload_cloudinary(dados, nome_arquivo, pasta="the_continental_prints"):
    # CORRIGIDO: Verifica se as credenciais da Cloudinary estão configuradas antes de tentar o upload
    if not all([CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET]):
        logger.error("Não é possível fazer upload para Cloudinary: credenciais ausentes.")
        return None

    try:
        loop = asyncio.get_event_loop()
        upload_func = partial(
            cloudinary.uploader.upload,
            io.BytesIO(dados),
            public_id=nome_arquivo.rsplit(".", 1)[0],
            folder=pasta,
            resource_type="image",
            overwrite=False,
        )
        resultado = await loop.run_in_executor(None, upload_func)
        if resultado and resultado.get("secure_url"):
            logger.info(f"Upload para Cloudinary bem-sucedido: {resultado.get('secure_url')}")
            return resultado.get("secure_url")
        else:
            logger.warning(f"Upload para Cloudinary falhou ou não retornou URL segura para {nome_arquivo}.")
            return None
    except Exception as e:
        logger.error(f"Erro ao fazer upload para Cloudinary para {nome_arquivo}: {e}", exc_info=True)
        return None

async def salvar_print_cloudinary(cdn_url, nome_arquivo):
    dados = await baixar_em_memoria(cdn_url)
    if not dados:
        logger.warning(f"Não foi possível baixar dados para salvar print de {cdn_url}.")
        return None
    return await fazer_upload_cloudinary(dados, nome_arquivo)