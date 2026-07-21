from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = BASE_DIR / "browser_profile"
PROGRESS_FILE = BASE_DIR / "progress.json"
RAW_DIR = BASE_DIR.parent / "raw" / "suporte"

# True = conecta no Chrome que você já tem aberto e logado (via CDP), sem pedir QR de novo.
# False = abre um Chromium separado controlado pelo Playwright (pede QR na 1ª vez).
USE_EXISTING_CHROME = False
CDP_URL = "http://localhost:9222"

# Sem filtro de nomes - percorre as conversas na ordem em que aparecem na barra lateral.
# Quantas conversas novas processar por execução - rode o script várias vezes para
# completar aos poucos. Ajustado para fechar ~100 conversas em 3 lotes (34+33+33).
MAX_CHATS_PER_RUN = 5  # TEMP: reduzido para este teste

# Não carrega mensagens mais antigas que isso (em dias), contando a partir de hoje.
HISTORY_DAYS = 2

# Pausas (segundos, min/max) entre ações - deixa o ritmo mais humano e reduz risco de bloqueio.
DELAY_BETWEEN_CHATS = (1.0, 3.0)
DELAY_BETWEEN_SCROLLS = (0.8, 2.0)

# Tempo "lendo" a conversa logo depois de abrir, antes de começar a rolar pra trás.
READING_DELAY = (1.5, 4.0)

# A cada N conversas (número sorteado dentro dessa faixa a cada vez), uma pausa mais
# longa - imita alguém que se distrai, atende algo, toma um café.
BREAK_EVERY_N_CHATS = (8, 14)
BREAK_DURATION = (20, 60)

# Trava de tempo total por execução (minutos), além do limite por quantidade de conversas.
MAX_SESSION_MINUTES = 25

MAX_SCROLL_ATTEMPTS = 500  # trava de segurança por conversa
SCROLL_STALL_LIMIT = 5  # nº de rolagens sem novos itens até considerar "acabou"
