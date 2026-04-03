import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

COOLDOWNS_FILE = "farm_cooldowns.json"

def carregar_cooldowns():
    """Carrega os cooldowns de farm de um arquivo JSON."""
    if not os.path.exists(COOLDOWNS_FILE):
        return {}
    try:
        with open(COOLDOWNS_FILE, "r", encoding="utf-8") as f:
            # Filtra cooldowns expirados ao carregar
            data = json.load(f)
            agora = datetime.now()
            cooldowns_ativos = {}
            for user_id, timestamp_str in data.items():
                try:
                    last_farm_time = datetime.fromisoformat(timestamp_str)
                    # Mantém apenas cooldowns que ainda não expiraram (ou que expirarão em breve)
                    # Para evitar que o arquivo cresça indefinidamente com entradas antigas
                    if (agora - last_farm_time).total_seconds() < (3600 * 2): # Ex: mantém por 2 horas após o último farm
                        cooldowns_ativos[user_id] = timestamp_str
                except ValueError:
                    logger.warning(f"Timestamp inválido para user_id {user_id} no {COOLDOWNS_FILE}. Ignorando.")
            return cooldowns_ativos
    except json.JSONDecodeError:
        logger.warning(f"Arquivo {COOLDOWNS_FILE} está vazio ou corrompido. Retornando dicionário vazio.")
        return {}
    except Exception as e:
        logger.error(f"Erro ao carregar cooldowns de {COOLDOWNS_FILE}: {e}", exc_info=True)
        return {}

def salvar_cooldowns(cooldowns: dict):
    """Salva os cooldowns de farm em um arquivo JSON."""
    try:
        with open(COOLDOWNS_FILE, "w", encoding="utf-8") as f:
            json.dump(cooldowns, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Erro ao salvar cooldowns em {COOLDOWNS_FILE}: {e}", exc_info=True)