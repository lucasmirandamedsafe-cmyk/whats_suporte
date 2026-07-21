import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import plotly.graph_objects as go
import streamlit as st

from dashboard.colors import CATEGORICAL, INK, SURFACE
from pipeline.db import get_conn
from pipeline.metrics import (
    distribuicao_categoria_grupos,
    distribuicao_tipo_erro_grupos,
    kpis_grupos,
    load_group_messages,
    volume_problemas_por_area,
    volume_problemas_por_periodo,
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
        return load_group_messages(conn)


df = get_data()

st.title("Grupos - Reclamações e Erros na Plataforma")
st.caption("Piauí Primeira Infância · mensagens de grupos (saúde, educação, assistência) classificadas quanto a reclamação/erro")

if df.empty:
    st.warning(
        "Nenhuma mensagem de grupo encontrada. Rode `python pipeline/parse_groups.py` e "
        "`python pipeline/classify_issues.py` antes de abrir esta página."
    )
    st.stop()

with st.sidebar:
    st.header("Filtros")
    areas_disponiveis = sorted(df["area"].dropna().unique().tolist())
    areas_selecionadas = st.multiselect("Área", areas_disponiveis, default=areas_disponiveis)

    if df["timestamp"].notna().any():
        min_date, max_date = df["timestamp"].min().date(), df["timestamp"].max().date()
        date_range = st.date_input("Período", (min_date, max_date), min_value=min_date, max_value=max_date)
    else:
        date_range = None

    apenas_problemas = st.checkbox("Mostrar só mensagens com problema na tabela", value=True)

if areas_selecionadas:
    df = df[df["area"].isin(areas_selecionadas)]

if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = date_range
    df = df[(df["timestamp"].dt.date >= start) & (df["timestamp"].dt.date <= end)]

if df.empty:
    st.info("Nenhuma mensagem no filtro selecionado.")
    st.stop()

k = kpis_grupos(df)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Mensagens analisadas", k["total_mensagens"])
c2.metric("Reclamações/erros identificados", k["total_problemas"])
c3.metric("% do total", f"{k['pct_problemas']}%")
c4.metric("% erro de app", f"{k['pct_erro_app']}%")
st.caption(
    "Reclamações/erros contam incidentes únicos (mensagens da mesma conversa, mesmo tipo e "
    "mesmo dia são agrupadas em 1), não cada mensagem individual."
)

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Problemas por área")
    vol_area = volume_problemas_por_area(df)
    fig = go.Figure(go.Bar(x=vol_area["area"], y=vol_area["problemas"], marker_color=CATEGORICAL[0]))
    fig.update_layout(**PLOTLY_LAYOUT, yaxis=dict(gridcolor=INK["grid"]), xaxis=dict(showgrid=False))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Distribuição por categoria")
    cat = distribuicao_categoria_grupos(df)
    fig = go.Figure(
        go.Bar(
            x=cat["categoria"],
            y=cat["incidentes"],
            marker_color=CATEGORICAL[1],
            text=cat["incidentes"],
            textposition="outside",
        )
    )
    fig.update_layout(**PLOTLY_LAYOUT, yaxis=dict(gridcolor=INK["grid"]), xaxis=dict(showgrid=False))
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Tipo de erro")
tipo_erro = distribuicao_tipo_erro_grupos(df)
if tipo_erro.empty:
    st.info(
        "Tipo de erro ainda nao classificado. Rode `python pipeline/classify_tipo_erro.py`."
    )
else:
    tipo_erro = tipo_erro.sort_values("incidentes")
    fig = go.Figure(
        go.Bar(
            x=tipo_erro["incidentes"],
            y=tipo_erro["tipo"],
            orientation="h",
            marker_color=CATEGORICAL[2],
            text=tipo_erro["incidentes"],
            textposition="outside",
        )
    )
    fig.update_layout(**PLOTLY_LAYOUT, xaxis=dict(gridcolor=INK["grid"]), yaxis=dict(showgrid=False))
    st.plotly_chart(fig, use_container_width=True)

col_titulo, col_toggle = st.columns([3, 1])
with col_titulo:
    st.subheader("Problemas ao longo do tempo")
with col_toggle:
    granularidade_label = st.radio(
        "Visualização",
        ["Diária", "Semanal", "Mensal"],
        horizontal=True,
        label_visibility="collapsed",
    )
granularidade = {"Diária": "dia", "Semanal": "semana", "Mensal": "mes"}[granularidade_label]

vol_periodo = volume_problemas_por_periodo(df, granularidade)
if not vol_periodo.empty:
    fig = go.Figure(go.Bar(x=vol_periodo["periodo"], y=vol_periodo["problemas"], marker_color=CATEGORICAL[5]))
    fig.update_layout(**PLOTLY_LAYOUT, yaxis=dict(gridcolor=INK["grid"]), xaxis=dict(showgrid=False))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nenhum problema no período selecionado.")

st.divider()
st.subheader("Mensagens")
tabela = df[df["is_issue"] == 1] if apenas_problemas else df
st.dataframe(
    tabela[
        ["timestamp", "area", "conversation_id", "sender", "issue_categoria", "issue_tipo", "issue_tema", "content"]
    ].sort_values("timestamp", ascending=False),
    use_container_width=True,
    hide_index=True,
)
