import json
import os
from datetime import datetime, timedelta

PRINTS_FILE   = "prints.json"
VALIDADE_DIAS = 14

def carregar_prints():
    if not os.path.exists(PRINTS_FILE):
        return []
    with open(PRINTS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def salvar_prints(dados):
    with open(PRINTS_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def registrar_print(user_id, cdn_url, nome_arquivo, cloudinary_url=None):
    dados = carregar_prints()
    expira_em = (datetime.now() + timedelta(days=VALIDADE_DIAS)).isoformat()
    dados.append({
        "user_id":        user_id,
        "cdn_url":        cdn_url,
        "cloudinary_url": cloudinary_url or "",
        "nome_arquivo":   nome_arquivo,
        "expira_em":      expira_em,
    })
    salvar_prints(dados)

def limpar_prints_expirados():
    dados = carregar_prints()
    agora = datetime.now()
    novos_dados = [d for d in dados if datetime.fromisoformat(d["expira_em"]) > agora]
    removidos = len(dados) - len(novos_dados)
    if removidos > 0:
        salvar_prints(novos_dados)
    return removidos