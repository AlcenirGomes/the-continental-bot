import json
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

PRINTS_FILE   = 'prints.json'
VALIDADE_DIAS = 14


def _load():
    if not os.path.exists(PRINTS_FILE):
        return []
    try:
        with open(PRINTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                migrado = []
                for user_id, entries in data.items():
                    for entry in entries:
                        migrado.append({
                            'user_id':        int(user_id),
                            'cdn_url':        entry.get('cdn_url', ''),
                            'cloudinary_url': entry.get('cloudinary_url', ''),
                            'nome_arquivo':   os.path.basename(entry.get('local_path', '')),
                            'expira_em':      entry.get('created_at', datetime.now().isoformat()),
                        })
                _save(migrado)
                return migrado
            return data
    except Exception:
        logger.exception('Erro ao carregar prints.json')
        return []


def _save(dados):
    try:
        with open(PRINTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
    except Exception:
        logger.exception('Erro ao salvar prints.json')


def registrar_print(user_id, cdn_url, nome_arquivo, cloudinary_url=None):
    dados = _load()
    expira_em = (datetime.now() + timedelta(days=VALIDADE_DIAS)).isoformat()
    dados.append({
        'user_id':        user_id,
        'cdn_url':        cdn_url,
        'cloudinary_url': cloudinary_url or '',
        'nome_arquivo':   nome_arquivo,
        'expira_em':      expira_em,
    })
    _save(dados)
    logger.info('Print registrado - user_id=%s cloudinary=%s', user_id, 'OK' if cloudinary_url else 'fallback CDN')


def limpar_prints_expirados():
    dados     = _load()
    agora     = datetime.now()
    validos   = []
    removidos = 0
    for entry in dados:
        try:
            expira_em = datetime.fromisoformat(entry.get('expira_em', '1970-01-01'))
        except ValueError:
            expira_em = datetime(1970, 1, 1)
        if expira_em <= agora:
            removidos += 1
        else:
            validos.append(entry)
    if removidos > 0:
        _save(validos)
        logger.info('Limpeza: %d print(s) removido(s).', removidos)
    return removidos