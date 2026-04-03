import json
import os
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

PRINTS_FILE   = "prints.json"
VALIDADE_DIAS = 14

def carregar_prints():
    if not os.path.exists(PRINTS_FILE):
        return []
    with open(PRINTS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"Arquivo {PRINTS_FILE} está vazio ou corrompido. Retornando lista vazia.")
            return []
        except Exception as e:
            logger.error(f"Erro ao carregar prints de {PRINTS_FILE}: {e}", exc_info=True)
            return []

def salvar_prints(dados):
    try:
        with open(PRINTS_FILE, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Erro ao salvar prints em {PRINTS_FILE}: {e}", exc_info=True)

def registrar_print(user_id: int, cdn_url: str, nome_arquivo: str):
    dados = carregar_prints()
    expira_em = (datetime.now() + timedelta(days=VALIDADE_DIAS)).isoformat()
    dados.append({
        "user_id":      user_id,
        "cdn_url":      cdn_url,
        "nome_arquivo": nome_arquivo,
        "expira_em":    expira_em,
    })
    salvar_prints(dados)
    logger.info(f"Print registrado para user_id {user_id}: {nome_arquivo}")

def limpar_prints_expirados():
    dados = carregar_prints()
    agora = datetime.now()
    novos = [d for d in dados if datetime.fromisoformat(d["expira_em"]) > agora]
    removidos = len(dados) - len(novos)
    if removidos > 0:
        salvar_prints(novos)
        logger.info(f"{removidos} prints expirados removidos.")
    return removidos