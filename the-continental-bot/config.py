from dotenv import load_dotenv
import os

load_dotenv()

CARGO_ID          = 1410706622317330633
CATEGORIA_FARM_ID = 1410706623865032719

# Marcadores invisíveis para o bot identificar as mensagens
ID_MARCADOR          = "\u200b" # Caractere de espaço de largura zero
ID_MARCADOR_REGISTRO = "\u200c" # Caractere de não-junção de largura zero
ID_MARCADOR_PEDIDO   = "\u200d" # Caractere de junção de largura zero

CANAL_REGISTRO_ID  = 1410706625374847115
CANAL_APROVACAO_ID = 1410706622317330640
CANAL_PEDIDO_ID    = 1410706623051202600
CANAL_LOG_ID       = 1410706622317330640

CARGOS_AUTORIZADOS = ["administrador", "01", "02", "03", "gerente"]

TOKEN = os.getenv("BOT_TOKEN")