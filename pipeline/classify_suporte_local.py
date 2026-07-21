"""Classificacao local (sem API) de reclamacao/erro nas mensagens do cliente no
suporte 1:1 - mesma taxonomia de categoria/tipo usada em group_messages
(classify_issues.py / classify_tipo_erro.py), so que via palavra-chave em vez de
LLM, porque Groq/Gemini nao estao disponiveis de forma confiavel neste projeto
(ver skill review-classification-quality). Da pra trocar por uma passada de LLM
depois sem mudar o schema - so reprocessar as linhas com analyzed_at IS NULL.

Uso: python pipeline/classify_suporte_local.py
"""
import re
import sys
import unicodedata
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.db import get_conn, init_db

# Mesma taxonomia de pipeline/classify_tipo_erro.py, pra comparar suporte 1:1
# com grupos usando as mesmas categorias. So entram frases que JA EMBUTEM
# linguagem de problema (nao so o assunto) - "cpf" ou "cadastro" sozinhos
# tambem aparecem quando o cliente so esta informando o proprio CPF/cadastro,
# sem reclamar de nada (mesmo erro que corrigimos na revisao de group_messages).
_TIPO_KEYWORDS = {
    "acesso_login": [
        "senha invalida", "senha errada", "usuario invalido", "usuario ou senha",
        "esqueci a senha", "esqueci minha senha", "resetar a senha", "reset de senha",
        "nao consigo entrar", "nao entra", "nao consigo acessar", "nao consigo logar",
        "bloqueado", "acesso bloqueado", "nao abre o app", "nao abre a plataforma",
        "conta bloqueada",
    ],
    "cadastro_dados": [
        "cadastro errado", "cadastrado errado", "dado errado", "dados errados",
        "cpf errado", "cpf invalido", "nao aceita o cpf", "nao aceita cpf",
        "nao consigo cadastrar", "erro no cadastro", "erro ao cadastrar",
        "nao consigo inserir", "nao consigo adicionar a familia",
    ],
    "visitas_acompanhamento": [
        "questionario nao salva", "formulario nao salva", "nao consigo preencher",
        "visita nao aparece", "nao consigo aplicar o questionario",
        "nao consigo fazer a visita", "plano de visita nao",
    ],
    "cursos_certificados": [
        "nao consigo emitir", "certificado nao aparece", "nao emite o certificado",
        "erro ao emitir certificado", "curso nao aparece", "nao consta o curso",
    ],
    "processo_administrativo": [
        "nao consigo aprovar", "nao aprova", "nao consigo excluir", "nao consigo vincular",
        "nao consigo desvincular", "unidade errada", "mais de uma unidade",
        "mais de um perfil", "nao vincula ao cras",
    ],
    "instabilidade_plataforma": [
        "nao funciona", "nao esta funcionando", "nao ta funcionando", "caiu",
        "travou", "esta travando", "bug", "muito lento", "lentidao", "instavel",
        "instabilidade", "fora do ar", "nao carrega", "nao salva", "erro ao salvar",
        "deu erro", "esta com erro", "dando erro", "tela branca", "nao abre",
    ],
}
_CATEGORIA_POR_TIPO = {
    "processo_administrativo": "processo_publico",
}
_PROBLEMA_GERAL = [
    "nao consigo", "nao aparece", "nao encontro", "sumiu", "sumiram",
    "da errado", "deu ruim", "nao deu certo", "nao funcionou", "que erro",
    "qual o erro", "aparece esse erro", "esse erro",
]


def _normalize(text):
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    return text.lower()


def classify_message(content: str):
    """Retorna (is_issue, categoria, tema, tipo). Local/keyword-based - sem LLM."""
    lowered = _normalize(content)
    for tipo, keywords in _TIPO_KEYWORDS.items():
        for kw in keywords:
            if kw in lowered:
                categoria = _CATEGORIA_POR_TIPO.get(tipo, "erro_app")
                return True, categoria, kw, tipo
    for kw in _PROBLEMA_GERAL:
        if kw in lowered:
            return True, "outro", kw, "outro"
    return False, None, None, None


def run(conn) -> int:
    rows = conn.execute(
        "SELECT id, content FROM messages WHERE is_support = 0 AND is_media = 0 AND analyzed_at IS NULL"
    ).fetchall()

    classificadas = 0
    for row in rows:
        is_issue, categoria, tema, tipo = classify_message(row["content"])
        conn.execute(
            """UPDATE messages
               SET is_issue = ?, issue_categoria = ?, issue_tema = ?, issue_tipo = ?,
                   analyzed_at = datetime('now')
               WHERE id = ?""",
            (1 if is_issue else 0, categoria, tema, tipo, row["id"]),
        )
        if is_issue:
            classificadas += 1
    conn.commit()
    return classificadas


def main():
    init_db()
    with get_conn() as conn:
        n = run(conn)
        total = conn.execute(
            "SELECT COUNT(*) c FROM messages WHERE is_support = 0 AND is_media = 0"
        ).fetchone()["c"]
    print(f"{n} mensagem(ns) de cliente marcada(s) como reclamacao/erro (de {total} mensagens de cliente analisadas).")


if __name__ == "__main__":
    main()
