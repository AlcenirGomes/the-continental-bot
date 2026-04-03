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

cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True,
)


async def baixar_em_memoria(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
                logger.warning('Falha ao baixar imagem - status %s', resp.status)
                return None
    except Exception:
        logger.exception('Erro ao baixar imagem de %s', url)
        return None


async def fazer_upload_cloudinary(dados, nome_arquivo, pasta='the_continental_prints'):
    try:
        loop = asyncio.get_event_loop()
        upload_func = partial(
            cloudinary.uploader.upload,
            io.BytesIO(dados),
            public_id=nome_arquivo.rsplit('.', 1)[0],
            folder=pasta,
            resource_type='image',
            overwrite=False,
        )
        resultado = await loop.run_in_executor(None, upload_func)
        url = resultado.get('secure_url')
        if url:
            logger.info('Upload Cloudinary OK: %s', url)
        return url
    except Exception:
        logger.exception('Erro ao fazer upload para Cloudinary')
        return None


async def salvar_print_cloudinary(cdn_url, nome_arquivo):
    dados = await baixar_em_memoria(cdn_url)
    if not dados:
        return None
    return await fazer_upload_cloudinary(dados, nome_arquivo)