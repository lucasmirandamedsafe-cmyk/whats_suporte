"""Funcoes puras que montam os dados do dashboard (Suporte e Grupos) a partir
de pipeline/metrics.py - nenhum calculo aqui, so carregamento + filtro (ver
api/filters.py) + chamada das funcoes que o antigo dashboard Streamlit ja
usava. Chamado por api/cli.py (um processo Python de uma vez so, sob demanda,
disparado pelas rotas do Next.js) - por isso nao ha cache em memoria aqui: o
processo nasce, calcula, imprime JSON e morre.
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.db import get_conn
from pipeline.metrics import (
    demandas_pouco_claras,
    distribuicao_categoria_grupos,
    distribuicao_categoria_suporte,
    distribuicao_tipo_erro_grupos,
    distribuicao_tipo_suporte,
    kpis,
    kpis_grupos,
    load_customer_messages,
    load_group_messages,
    load_sessions,
    pico_simultaneos_por_periodo,
    volume_por_dia,
    volume_por_hora,
    volume_problemas_por_area,
    volume_problemas_por_periodo,
)

from api.filters import apply_grupos_filters, apply_suporte_filters
from api.serialization import df_to_records


def suporte_filtros() -> dict:
    with get_conn() as conn:
        df = load_sessions(conn)
        msgs_cliente = load_customer_messages(conn)

    if df.empty:
        return {
            "has_data": False,
            "min_date": None,
            "max_date": None,
            "categorias": [],
            "categorias_erro": [],
            "tipos_erro": [],
        }

    return {
        "has_data": True,
        "min_date": df["started_at"].min().date().isoformat(),
        "max_date": df["started_at"].max().date().isoformat(),
        "categorias": sorted(df["categoria"].dropna().unique().tolist()),
        "categorias_erro": sorted(msgs_cliente["issue_categoria"].dropna().unique().tolist()),
        "tipos_erro": sorted(msgs_cliente["issue_tipo"].dropna().unique().tolist()),
    }


def suporte_dashboard(
    start: date | None = None,
    end: date | None = None,
    categoria: str | None = None,
    categoria_erro: str | None = None,
    tipo_erro: str | None = None,
) -> dict:
    with get_conn() as conn:
        df_sessions = load_sessions(conn)
        msgs_cliente = load_customer_messages(conn)
        clareza = demandas_pouco_claras(conn)

    filtered = apply_suporte_filters(
        df_sessions, msgs_cliente, clareza, start, end, categoria, categoria_erro, tipo_erro
    )
    df = filtered["df"]
    msgs_filtradas = filtered["msgs_filtradas"]
    reclamacoes_filtradas = filtered["reclamacoes_filtradas"]
    pct_pouco_clara = filtered["pct_pouco_clara"]

    if df.empty:
        pico_atual = 0
    else:
        pico_serie = pico_simultaneos_por_periodo(df, "dia")["pico_simultaneos"]
        pico_atual = int(pico_serie.max()) if not pico_serie.empty else 0

    k = kpis(df)
    tempo_medio = k["tempo_resposta_medio_min"]

    total_msgs_cliente = len(msgs_filtradas)
    total_reclamacoes = len(reclamacoes_filtradas)
    pct_reclamacoes = round(total_reclamacoes / total_msgs_cliente * 100, 1) if total_msgs_cliente else 0

    tipo_erro_dist = distribuicao_tipo_suporte(reclamacoes_filtradas)
    if not tipo_erro_dist.empty:
        tipo_erro_dist = tipo_erro_dist.sort_values("mensagens")

    return {
        "kpis": {
            "total_sessoes": k["total_sessoes"],
            "tempo_resposta_medio_min": tempo_medio,
            "tempo_resposta_medio_min_display": f"{tempo_medio} min" if tempo_medio is not None else "—",
            "tempo_resposta_mediano_min": k["tempo_resposta_mediano_min"],
            "pct_reclamacao": k["pct_reclamacao"],
            "pct_duvida": k["pct_duvida"],
            "pico_simultaneos": pico_atual,
            "pct_pouco_clara": pct_pouco_clara,
            "pct_pouco_clara_display": f"{pct_pouco_clara}%",
        },
        "kpis_reclamacao": {
            "total_mensagens_cliente": total_msgs_cliente,
            "total_reclamacoes": total_reclamacoes,
            "pct_reclamacoes": pct_reclamacoes,
            "pct_reclamacoes_display": f"{pct_reclamacoes}%",
        },
        "volume_por_dia": df_to_records(volume_por_dia(df)),
        "volume_por_hora": df_to_records(volume_por_hora(df)),
        "atendimentos_simultaneos": {
            "dia": df_to_records(pico_simultaneos_por_periodo(df, "dia")),
            "semana": df_to_records(pico_simultaneos_por_periodo(df, "semana")),
            "mes": df_to_records(pico_simultaneos_por_periodo(df, "mes")),
        },
        "distribuicao_categoria_erro": df_to_records(distribuicao_categoria_suporte(reclamacoes_filtradas)),
        "distribuicao_tipo_erro": df_to_records(tipo_erro_dist),
        "mensagens_reclamacao": df_to_records(
            reclamacoes_filtradas[["timestamp", "conversation_id", "issue_categoria", "issue_tipo", "content"]]
            .sort_values("timestamp", ascending=False)
        ),
        "atendimentos": df_to_records(
            df[["started_at", "conversation_id", "categoria", "tema", "resumo", "first_response_seconds"]]
            .sort_values("started_at", ascending=False)
        ),
    }


def grupos_filtros() -> dict:
    with get_conn() as conn:
        df = load_group_messages(conn)

    if df.empty:
        return {"has_data": False, "areas": [], "min_date": None, "max_date": None}

    tem_timestamp = df["timestamp"].notna().any()
    return {
        "has_data": True,
        "areas": sorted(df["area"].dropna().unique().tolist()),
        "min_date": df["timestamp"].min().date().isoformat() if tem_timestamp else None,
        "max_date": df["timestamp"].max().date().isoformat() if tem_timestamp else None,
    }


def grupos_dashboard(
    areas: list[str] | None = None,
    start: date | None = None,
    end: date | None = None,
) -> dict:
    with get_conn() as conn:
        df_group_msgs = load_group_messages(conn)

    df = apply_grupos_filters(df_group_msgs, areas, start, end)

    if df.empty:
        return {
            "is_empty": True,
            "kpis": {
                "total_mensagens": 0,
                "total_problemas": 0,
                "pct_problemas": 0,
                "pct_problemas_display": "0%",
                "pct_erro_app": 0,
                "pct_erro_app_display": "0%",
            },
            "volume_por_area": [],
            "distribuicao_categoria": [],
            "distribuicao_tipo_erro": [],
            "problemas_por_periodo": {"dia": [], "semana": [], "mes": []},
            "mensagens": [],
        }

    k = kpis_grupos(df)

    tipo_erro_dist = distribuicao_tipo_erro_grupos(df)
    if not tipo_erro_dist.empty:
        tipo_erro_dist = tipo_erro_dist.sort_values("incidentes")

    return {
        "is_empty": False,
        "kpis": {
            "total_mensagens": k["total_mensagens"],
            "total_problemas": k["total_problemas"],
            "pct_problemas": k["pct_problemas"],
            "pct_problemas_display": f"{k['pct_problemas']}%",
            "pct_erro_app": k["pct_erro_app"],
            "pct_erro_app_display": f"{k['pct_erro_app']}%",
        },
        "volume_por_area": df_to_records(volume_problemas_por_area(df)),
        "distribuicao_categoria": df_to_records(distribuicao_categoria_grupos(df)),
        "distribuicao_tipo_erro": df_to_records(tipo_erro_dist),
        "problemas_por_periodo": {
            "dia": df_to_records(volume_problemas_por_periodo(df, "dia")),
            "semana": df_to_records(volume_problemas_por_periodo(df, "semana")),
            "mes": df_to_records(volume_problemas_por_periodo(df, "mes")),
        },
        "mensagens": df_to_records(
            df[
                [
                    "timestamp",
                    "area",
                    "conversation_id",
                    "sender",
                    "issue_categoria",
                    "issue_tipo",
                    "issue_tema",
                    "content",
                    "is_issue",
                ]
            ].sort_values("timestamp", ascending=False)
        ),
    }
