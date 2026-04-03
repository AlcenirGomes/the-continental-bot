import os
from dotenv import load_dotenv

load_dotenv()

# --- IDs de Canais, Categorias e Cargos ---
CARGO_ID          = 1410706622317330633 # Verifique se este ID ainda é relevante
CATEGORIA_FARM_ID = 1410706623865032719

# Marcadores invisíveis para o bot identificar as mensagens
ID_MARCADOR          = "\u200b" # Caractere de espaço de largura zero (para Farm)
ID_MARCADOR_REGISTRO = "\u200c" # Caractere de não-junção de largura zero (para Registro)
ID_MARCADOR_PEDIDO   = "\u200d" # Caractere de junção de largura zero (para Pedido)

CANAL_REGISTRO_ID  = 1410706625374847115
CANAL_APROVACAO_ID = 1410706622317330640
CANAL_PEDIDO_ID    = 1410706623051202600
CANAL_LOG_ID       = 1410706622317330640 # Verifique se CANAL_APROVACAO_ID e CANAL_LOG_ID são o mesmo canal intencionalmente

CARGOS_AUTORIZADOS = ["administrador", "01", "02", "03", "gerente"]

# --- Variáveis de Ambiente ---
TOKEN = os.getenv("DISCORD_BOT_TOKEN") # CORRIGIDO: Nome da variável para corresponder ao .env
if TOKEN is None:
    raise ValueError("O token do Discord não foi encontrado nas variáveis de ambiente. Verifique seu arquivo .env.")

ENVIRONMENT = os.getenv("ENVIRONMENT", "production") # Padrão para 'production' se não estiver definido no .env
PREFIX = "!" # Prefixo para comandos de texto (se usados)