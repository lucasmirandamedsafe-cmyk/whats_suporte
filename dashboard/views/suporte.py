import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import plotly.graph_objects as go
import streamlit as st

from dashboard.colors import CATEGORICAL, INK, SURFACE
from pipeline.db import get_conn
from pipeline.metrics import (
    demandas_pouco_claras,
    distribuicao_categoria_suporte,
    distribuicao_tipo_suporte,
    kpis,
    kpis_reclamacao_suporte,
    load_customer_messages,
    load_sessions,
    pico_simultaneos_por_periodo,
    volume_por_dia,
    volume_por_hora,
)

PLOTLY_LAYOUT = dict(
    paper_bgcolor=SURFACE,
    plot_bgcolor=SURFACE,
    font=dict(color=INK["primary"], family="system-ui, -apple-system, Segoe UI, sans-serif"),
    margin=dict(l=10, r=10, t=30, b=10),
)


@st.cache_data(ttl=60)
def get_data():
    with get_conn() as conn:
        return load_sessions(conn)


@st.cache_data(ttl=60)
def get_clareza():
    with get_conn() as conn:
        return demandas_pouco_claras(conn)


@st.cache_data(ttl=60)
def get_mensagens_cliente():
    with get_conn() as conn:
        return load_customer_messages(conn)


df = get_data()

st.title("Suporte WhatsApp")

if df.empty:
    st.warning("Nenhum dado encontrado. Rode `python pipeline/sync_data.py` antes de abrir o dashboard.")
    st.stop()

with st.sidebar:
    st.header("Filtros")
    min_date, max_date = df["started_at"].min().date(), df["started_at"].max().date()
    date_range = st.date_input("Período", (min_date, max_date), min_value=min_date, max_value=max_date)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = date_range
    df = df[(df["started_at"].dt.date >= start) & (df["started_at"].dt.date <= end)]

clareza = get_clareza()
clareza_filtrada = clareza[clareza["session_id"].isin(df["session_id"])]
pct_pouco_clara = round(clareza_filtrada["demanda_pouco_clara"].mean() * 100, 1) if not clareza_filtrada.empty else 0

msgs_cliente = get_mensagens_cliente()
conversas_no_filtro = set(df["conversation_id"])
msgs_filtradas = msgs_cliente[
    msgs_cliente["conversation_id"].isin(conversas_no_filtro)
    & (msgs_cliente["timestamp"].dt.date >= df["started_at"].min().date())
    & (msgs_cliente["timestamp"].dt.date <= df["started_at"].max().date())
] if not df.empty else msgs_cliente.iloc[0:0]
k_reclamacao = kpis_reclamacao_suporte(msgs_filtradas)

if df.empty:
    pico_atual = 0
else:
    pico_serie = pico_simultaneos_por_periodo(df, "dia")["pico_simultaneos"]
    pico_atual = int(pico_serie.max()) if not pico_serie.empty else 0

k = kpis(df)
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Atendimentos", k["total_sessoes"])
c2.metric(
    "Tempo médio de resposta",
    f"{k['tempo_resposta_medio_min']} min" if k["tempo_resposta_medio_min"] is not None else "—",
)
c3.metric("Pico simultâneos", pico_atual)
c4.metric("% Demanda pouco clara", f"{pct_pouco_clara}%")
c5.metric("Reclamações de erro", k_reclamacao["total_reclamacoes"])
c6.metric("% msgs com reclamação", f"{k_reclamacao['pct_reclamacoes']}%")
st.caption(
    "Pico simultâneos: maior nº de atendimentos abertos ao mesmo tempo em um único dia. "
    "Demanda pouco clara: heurística local (sem IA) - mensagem inicial curta/sem detalhe do "
    "problema, ou suporte precisou dizer que não entendeu. Reclamações de erro: classificação "
    "local por palavra-chave (sem IA) das mensagens do cliente - ver pipeline/classify_suporte_local.py."
)

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Volume de atendimentos por dia")
    vol = volume_por_dia(df)
    fig = go.Figure(go.Bar(x=vol["dia"], y=vol["conversas"], marker_color=CATEGORICAL[0]))
    fig.update_layout(**PLOTLY_LAYOUT, yaxis=dict(gridcolor=INK["grid"]), xaxis=dict(showgrid=False))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Volume por hora do dia")
    vol_h = volume_por_hora(df)
    fig = go.Figure(go.Bar(x=vol_h["hora"], y=vol_h["conversas"], marker_color=CATEGORICAL[0]))
    fig.update_layout(**PLOTLY_LAYOUT, yaxis=dict(gridcolor=INK["grid"]), xaxis=dict(showgrid=False, dtick=1))
    st.plotly_chart(fig, use_container_width=True)

col_titulo, col_toggle = st.columns([3, 1])
with col_titulo:
    st.subheader("Atendimentos simultâneos")
with col_toggle:
    granularidade_label = st.radio(
        "Visualização",
        ["Diária", "Semanal", "Mensal"],
        horizontal=True,
        label_visibility="collapsed",
        key="granularidade_simultaneos",
    )
granularidade = {"Diária": "dia", "Semanal": "semana", "Mensal": "mes"}[granularidade_label]
pico = pico_simultaneos_por_periodo(df, granularidade)
if not pico.empty:
    fig = go.Figure(go.Bar(x=pico["periodo"], y=pico["pico_simultaneos"], marker_color=CATEGORICAL[3]))
    fig.update_layout(**PLOTLY_LAYOUT, yaxis=dict(gridcolor=INK["grid"]), xaxis=dict(showgrid=False))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sem atendimentos no período selecionado.")

st.divider()
st.subheader("Reclamações de erro")
st.caption(
    "Mensagens do cliente (fora do suporte) que expressam uma reclamação ou relatam um "
    "erro/problema na plataforma - mesma taxonomia de categoria/tipo usada em Grupos."
)

col3, col4 = st.columns(2)

with col3:
    st.subheader("Distribuição por categoria")
    cat = distribuicao_categoria_suporte(msgs_filtradas)
    if cat.empty:
        st.info("Nenhuma reclamação no período selecionado.")
    else:
        fig = go.Figure(
            go.Bar(
                x=cat["categoria"],
                y=cat["mensagens"],
                marker_color=CATEGORICAL[1],
                text=cat["mensagens"],
                textposition="outside",
            )
        )
        fig.update_layout(**PLOTLY_LAYOUT, yaxis=dict(gridcolor=INK["grid"]), xaxis=dict(showgrid=False))
        st.plotly_chart(fig, use_container_width=True)

with col4:
    st.subheader("Tipo de erro")
    tipo = distribuicao_tipo_suporte(msgs_filtradas)
    if tipo.empty:
        st.info("Nenhuma reclamação no período selecionado.")
    else:
        tipo = tipo.sort_values("mensagens")
        fig = go.Figure(
            go.Bar(
                x=tipo["mensagens"],
                y=tipo["tipo"],
                orientation="h",
                marker_color=CATEGORICAL[2],
                text=tipo["mensagens"],
                textposition="outside",
            )
        )
        fig.update_layout(**PLOTLY_LAYOUT, xaxis=dict(gridcolor=INK["grid"]), yaxis=dict(showgrid=False))
        st.plotly_chart(fig, use_container_width=True)

st.subheader("Mensagens com reclamação/erro")
reclamacoes = msgs_filtradas[msgs_filtradas["is_issue"] == 1]
st.dataframe(
    reclamacoes[["timestamp", "conversation_id", "issue_categoria", "issue_tipo", "content"]]
    .sort_values("timestamp", ascending=False),
    use_container_width=True,
    hide_index=True,
)

st.divider()
st.subheader("Demandas pouco claras")
st.caption(
    "Atendimentos cuja mensagem inicial do cliente (antes da 1ª resposta do suporte) veio "
    "curta/sem detalhe do problema, ou em que o suporte precisou dizer que não entendeu."
)
pouco_claras = df.merge(clareza_filtrada[["session_id", "mensagem_inicial", "demanda_pouco_clara"]], on="session_id")
pouco_claras = pouco_claras[pouco_claras["demanda_pouco_clara"]]
st.dataframe(
    pouco_claras[["started_at", "conversation_id", "mensagem_inicial", "first_response_seconds"]]
    .sort_values("started_at", ascending=False),
    use_container_width=True,
    hide_index=True,
)

st.divider()
st.subheader("Atendimentos")
st.dataframe(
    df[["started_at", "conversation_id", "categoria", "tema", "resumo", "first_response_seconds"]]
    .sort_values("started_at", ascending=False),
    use_container_width=True,
    hide_index=True,
)
