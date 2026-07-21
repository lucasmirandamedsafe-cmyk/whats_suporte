import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "raw" / "suporte"
DB_PATH = BASE_DIR / "data" / "whatsapp.db"

# Nomes exatamente como aparecem no export do WhatsApp para identificar
# mensagens do suporte/negócio (comparação é por substring, case-insensitive).
# Ex.: se o export mostra "Suporte Loja X: mensagem", coloque "Suporte Loja X".
SUPPORT_SENDER_NAMES = [
    "Suporte Técnico",
]

# Gap (em horas) sem mensagens que marca o início de um novo atendimento/sessão
# dentro da mesma conversa.
SESSION_GAP_HOURS = 6

# Groq classifica categoria/tema/sentimento (barato e rápido, roda em lote)
# Modelos disponíveis: https://console.groq.com/docs/models
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Gemini gera o resumo de cada atendimento (free tier generoso, boa qualidade de texto)
# Crie uma key gratuita em https://aistudio.google.com/apikey
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
