"""Port literal da logica de filtro que hoje vive em dashboard/views/*.py -
ainda pandas puro, copiada linha a linha, sem reinterpretar. Nenhuma funcao
aqui faz calculo de metrica (isso continua 100% em pipeline/metrics.py) - so
recorta o DataFrame antes de repassar pra la, exatamente como os views do
Streamlit fazem antes de chamar as mesmas funcoes.
"""
from datetime import date

import pandas as pd


def apply_suporte_filters(
    df_sessions: pd.DataFrame,
    msgs_cliente: pd.DataFrame,
    clareza: pd.DataFrame,
    start: date | None,
    end: date | None,
    categoria: str | None,
    categoria_erro: str | None,
    tipo_erro: str | None,
) -> dict:
    df = df_sessions

    # Periodo - mesmo comportamento do st.date_input com default (min, max):
    # sem start/end informados, usa o range completo (equivalente a "sem filtro").
    if not df.empty:
        min_date = df["started_at"].min().date()
        max_date = df["started_at"].max().date()
        start = start or min_date
        end = end or max_date
        df = df[(df["started_at"].dt.date >= start) & (df["started_at"].dt.date <= end)]

    # Categoria do atendimento - filtra a base inteira (afeta todos os KPIs/graficos
    # de sessao e a tabela "Atendimentos").
    if categoria:
        df = df[df["categoria"] == categoria]

    # % Demanda pouco clara - calculado sobre as sessoes ja filtradas acima.
    clareza_filtrada = clareza[clareza["session_id"].isin(df["session_id"])]
    pct_pouco_clara = (
        round(clareza_filtrada["demanda_pouco_clara"].mean() * 100, 1) if not clareza_filtrada.empty else 0
    )

    # Mensagens do cliente no mesmo recorte de conversas + periodo das sessoes
    # filtradas - essa e' a base (denominador) do "% msgs com reclamacao",
    # calculada ANTES de aplicar categoria_erro/tipo_erro.
    if not df.empty:
        conversas_no_filtro = set(df["conversation_id"])
        msgs_filtradas = msgs_cliente[
            msgs_cliente["conversation_id"].isin(conversas_no_filtro)
            & (msgs_cliente["timestamp"].dt.date >= df["started_at"].min().date())
            & (msgs_cliente["timestamp"].dt.date <= df["started_at"].max().date())
        ]
    else:
        msgs_filtradas = msgs_cliente.iloc[0:0]

    # Categoria de erro / Tipo de erro - filtram SO a secao "Reclamacoes de erro"
    # (seus proprios KPIs, graficos e tabela), sem encolher total_msgs_cliente.
    reclamacoes_filtradas = msgs_filtradas[msgs_filtradas["is_issue"] == 1]
    if categoria_erro:
        reclamacoes_filtradas = reclamacoes_filtradas[reclamacoes_filtradas["issue_categoria"] == categoria_erro]
    if tipo_erro:
        reclamacoes_filtradas = reclamacoes_filtradas[reclamacoes_filtradas["issue_tipo"] == tipo_erro]

    return {
        "df": df,
        "msgs_filtradas": msgs_filtradas,
        "reclamacoes_filtradas": reclamacoes_filtradas,
        "pct_pouco_clara": pct_pouco_clara,
    }


def apply_grupos_filters(
    df_group_msgs: pd.DataFrame,
    areas: list[str] | None,
    start: date | None,
    end: date | None,
) -> pd.DataFrame:
    df = df_group_msgs

    if areas:
        df = df[df["area"].isin(areas)]

    if df["timestamp"].notna().any():
        min_date = df["timestamp"].min().date()
        max_date = df["timestamp"].max().date()
        start = start or min_date
        end = end or max_date
        df = df[(df["timestamp"].dt.date >= start) & (df["timestamp"].dt.date <= end)]

    return df
