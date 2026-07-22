"""Confere que api/dashboard_data.py devolve os MESMOS numeros que uma chamada
direta a pipeline.metrics sobre o mesmo DataFrame filtrado manualmente - a
garantia de que a camada de API/filtro nao introduziu nenhuma divergencia de
calculo.

Roda contra o data/whatsapp.db real (leitura apenas). Uso: pytest api/tests/
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from api.dashboard_data import grupos_dashboard, suporte_dashboard
from pipeline.db import get_conn
from pipeline.metrics import (
    kpis,
    kpis_grupos,
    load_customer_messages,
    load_group_messages,
    load_sessions,
)


def test_suporte_dashboard_sem_filtro_bate_com_pipeline_metrics():
    with get_conn() as conn:
        df = load_sessions(conn)
    esperado = kpis(df)

    resultado = suporte_dashboard()
    kpis_api = resultado["kpis"]

    assert kpis_api["total_sessoes"] == esperado["total_sessoes"]
    assert kpis_api["tempo_resposta_medio_min"] == esperado["tempo_resposta_medio_min"]
    assert kpis_api["tempo_resposta_mediano_min"] == esperado["tempo_resposta_mediano_min"]
    assert kpis_api["pct_reclamacao"] == esperado["pct_reclamacao"]
    assert kpis_api["pct_duvida"] == esperado["pct_duvida"]


def test_suporte_dashboard_filtrado_por_categoria_bate_com_pipeline_metrics():
    with get_conn() as conn:
        df = load_sessions(conn)
    df_filtrado = df[df["categoria"] == "reclamacao"]
    esperado = kpis(df_filtrado)

    resultado = suporte_dashboard(categoria="reclamacao")
    kpis_api = resultado["kpis"]

    assert kpis_api["total_sessoes"] == esperado["total_sessoes"]
    assert kpis_api["pct_reclamacao"] == esperado["pct_reclamacao"]
    assert kpis_api["pct_duvida"] == esperado["pct_duvida"]


def test_suporte_filtro_erro_nao_encolhe_denominador():
    sem_filtro = suporte_dashboard()
    com_filtro = suporte_dashboard(tipo_erro="acesso_login")

    # total_sessoes e total_mensagens_cliente nao mudam so por filtrar tipo de erro.
    assert com_filtro["kpis"]["total_sessoes"] == sem_filtro["kpis"]["total_sessoes"]
    assert (
        com_filtro["kpis_reclamacao"]["total_mensagens_cliente"]
        == sem_filtro["kpis_reclamacao"]["total_mensagens_cliente"]
    )
    # so o numerador (reclamacoes) encolhe.
    assert (
        com_filtro["kpis_reclamacao"]["total_reclamacoes"] <= sem_filtro["kpis_reclamacao"]["total_reclamacoes"]
    )


def test_grupos_dashboard_sem_filtro_bate_com_pipeline_metrics():
    with get_conn() as conn:
        df = load_group_messages(conn)
    esperado = kpis_grupos(df)

    resultado = grupos_dashboard()
    kpis_api = resultado["kpis"]

    assert kpis_api["total_mensagens"] == esperado["total_mensagens"]
    assert kpis_api["total_problemas"] == esperado["total_problemas"]
    assert kpis_api["pct_problemas"] == esperado["pct_problemas"]
    assert kpis_api["pct_erro_app"] == esperado["pct_erro_app"]


def test_grupos_dashboard_filtrado_por_area_bate_com_pipeline_metrics():
    with get_conn() as conn:
        df = load_group_messages(conn)
    df_filtrado = df[df["area"].isin(["assistencia"])]
    esperado = kpis_grupos(df_filtrado)

    resultado = grupos_dashboard(areas=["assistencia"])
    kpis_api = resultado["kpis"]

    assert kpis_api["total_mensagens"] == esperado["total_mensagens"]
    assert kpis_api["total_problemas"] == esperado["total_problemas"]


def test_suporte_mensagens_da_categoria_nao_vazam_de_outras_sessoes():
    """Regressao: total_mensagens_cliente/total_reclamacoes de um filtro de
    categoria devem vir SO das sessoes com aquela categoria - nao de outras
    sessoes do mesmo cliente (mesmo conversation_id) que caiam dentro da
    janela de datas entre a primeira e a ultima sessao filtrada."""
    with get_conn() as conn:
        df = load_sessions(conn)
        msgs = load_customer_messages(conn)

    sessoes_elogio = df[df["categoria"] == "elogio"]
    if sessoes_elogio.empty:
        return  # nao ha dados suficientes pra este cenario nesta base

    ids_elogio = set(sessoes_elogio["session_id"])
    esperado_msgs = msgs[msgs["session_id"].isin(ids_elogio)]
    esperado_reclamacoes = esperado_msgs[esperado_msgs["is_issue"] == 1]

    resultado = suporte_dashboard(categoria="elogio")

    assert resultado["kpis_reclamacao"]["total_mensagens_cliente"] == len(esperado_msgs)
    assert resultado["kpis_reclamacao"]["total_reclamacoes"] == len(esperado_reclamacoes)


def test_display_fields_never_drop_decimal():
    resultado = suporte_dashboard()
    display = resultado["kpis"]["pct_pouco_clara_display"]
    valor = resultado["kpis"]["pct_pouco_clara"]
    assert display == f"{valor}%"
    assert "." in display or valor == 0
