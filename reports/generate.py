"""Gera o relatorio PDF de Suporte a partir dos mesmos dados e filtros do
dashboard - reusa api/filters.py::apply_suporte_filters e as funcoes de
pipeline/metrics.py (nenhum calculo novo aqui, so leitura + escrita em PDF).
Chamado por `python -m api.cli suporte-relatorio-pdf` (usado pela rota
/api/suporte/relatorio-pdf do Next.js) ou standalone via
`python reports/generate.py [--start] [--end] [--categoria] [--tipo-erro]`.
"""
import argparse
import sys
from datetime import date, datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fpdf import FPDF

from api.filters import apply_suporte_filters
from pipeline.db import get_conn
from pipeline.metrics import (
    demandas_pouco_claras,
    distribuicao_tipo_suporte,
    kpis,
    load_all_messages,
    load_customer_messages,
    load_sessions,
    media_atendimentos_por_hora,
    pico_simultaneos_por_periodo,
    ranking_temas,
    volume_atendimentos_por_periodo,
    volume_mensagens_por_periodo,
    volume_por_dia_semana_hora,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "output"

# Mesma paleta de web/src/components/charts/chartTheme.ts (CATEGORICAL/STATUS/INK)
# - o PDF usa as mesmas cores dos graficos do dashboard, so em RGB pro fpdf2.
_AZUL = (42, 120, 214)
_VERDE = (0, 131, 0)
_ROSA = (232, 123, 164)
_AMBAR = (237, 161, 0)
_VERDE_AGUA = (27, 175, 122)
_LARANJA = (235, 104, 52)
_ROXO = (74, 58, 167)
_VERMELHO = (227, 73, 72)
_CATEGORICAL = [_AZUL, _VERDE, _ROSA, _AMBAR, _VERDE_AGUA, _LARANJA, _ROXO, _VERMELHO]

_INK_PRIMARY = (11, 11, 11)
_INK_SECONDARY = (82, 81, 78)
_INK_MUTED = (137, 135, 129)
_GRID = (225, 224, 217)
_SURFACE = (250, 250, 248)

_LARGURA_CONTEUDO = 190  # A4 (210mm) - margens de 10mm dos dois lados

# A fonte core "Helvetica" do fpdf2 so cobre latin-1 - os acentos do portugues
# passam direto, mas travessao/aspas tipograficas (usados em faixa_hora, por
# exemplo "06h-08h" com en dash) precisam virar equivalente ASCII antes de ir
# pro PDF.
_SUBSTITUICOES_UNICODE = {
    "–": "-", "—": "-", "‘": "'", "’": "'", "“": '"', "”": '"',
}


def _sanitize(texto: str) -> str:
    """Normaliza travessao/aspas tipograficas e descarta qualquer outro
    caractere fora do latin-1 (ex: emoji em mensagens reais dos clientes) -
    a fonte core do fpdf2 nao suporta unicode completo."""
    for original, novo in _SUBSTITUICOES_UNICODE.items():
        texto = texto.replace(original, novo)
    return texto.encode("latin-1", errors="replace").decode("latin-1")


class Report(FPDF):
    def __init__(self, filtros_label: str):
        super().__init__()
        self.filtros_label = filtros_label
        self.alias_nb_pages()
        self.set_auto_page_break(auto=True, margin=18)

    def header(self):
        self.set_fill_color(*_AZUL)
        self.rect(0, 0, self.w, 24, style="F")
        self.set_xy(10, 6)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 16)
        self.cell(0, 7, "Relatorio de Suporte - WhatsApp", new_x="LMARGIN", new_y="NEXT")
        self.set_x(10)
        self.set_font("Helvetica", "", 9.5)
        self.cell(0, 5, "Piaui Primeira Infancia", new_x="LMARGIN", new_y="NEXT")

        self.set_xy(10, 27)
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*_INK_MUTED)
        self.cell(0, 4, _sanitize(f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}"), new_x="LMARGIN", new_y="NEXT")
        self.set_x(10)
        self.cell(0, 4, _sanitize(self.filtros_label), new_x="LMARGIN", new_y="NEXT")

        self.set_text_color(*_INK_PRIMARY)
        self.set_font("Helvetica", "", 10)
        self.set_y(37)

    def footer(self):
        self.set_y(-15)
        self.set_draw_color(*_GRID)
        self.line(10, self.get_y(), 10 + _LARGURA_CONTEUDO, self.get_y())
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*_INK_MUTED)
        self.cell(0, 8, f"Pagina {self.page_no()}/{{nb}}", align="C")
        self.set_text_color(*_INK_PRIMARY)

    def section(self, title: str, color=_AZUL):
        self.ln(3)
        # Garante que o titulo + pelo menos uma linha de conteudo cabem antes
        # de desenhar a barra colorida - senao ela fica orfa no fim da pagina
        # anterior enquanto o texto pula pra proxima (add_page so e' acionado
        # automaticamente dentro de cell/multi_cell, depois do rect ja desenhado).
        if self.get_y() + 16 > self.page_break_trigger:
            self.add_page()
        y = self.get_y()
        self.set_fill_color(*color)
        self.rect(self.l_margin, y + 1, 3, 5.5, style="F")
        self.set_xy(self.l_margin + 6, y)
        self.set_font("Helvetica", "B", 12.5)
        self.set_text_color(*_INK_PRIMARY)
        self.cell(0, 7, _sanitize(title), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_font("Helvetica", "", 10)

    def paragrafo(self, texto: str):
        self.set_text_color(*_INK_SECONDARY)
        self.multi_cell(0, 5.5, _sanitize(texto), align="L")
        self.set_text_color(*_INK_PRIMARY)
        self.ln(1)

    def bullet(self, texto: str, color=_AZUL):
        x0, y0 = self.l_margin, self.get_y()
        self.set_fill_color(*color)
        self.rect(x0 + 1, y0 + 2, 2.2, 2.2, style="F")
        self.set_xy(x0 + 6, y0)
        self.set_text_color(*_INK_SECONDARY)
        self.multi_cell(_LARGURA_CONTEUDO - 6, 5.5, _sanitize(texto), align="L", markdown=True)
        self.set_text_color(*_INK_PRIMARY)

    def kpi_grid(self, itens, cols=3, altura=23):
        """itens: lista de (label, valor, cor). Desenha um grid de cartoes -
        mesmo espirito visual dos KpiCard do dashboard web, so que em PDF."""
        gap = 5
        largura = (_LARGURA_CONTEUDO - gap * (cols - 1)) / cols
        linhas_totais = -(-len(itens) // cols)
        if self.get_y() + linhas_totais * (altura + gap) > self.page_break_trigger:
            self.add_page()
        x0, y0 = self.l_margin, self.get_y()
        for i, (label, valor, color) in enumerate(itens):
            col, row = i % cols, i // cols
            x = x0 + col * (largura + gap)
            y = y0 + row * (altura + gap)
            self.set_draw_color(*_GRID)
            self.set_fill_color(*_SURFACE)
            self.rect(x, y, largura, altura, style="DF", round_corners=True, corner_radius=2)
            self.set_fill_color(*color)
            self.rect(x, y, 1.6, altura, style="F", round_corners=True, corner_radius=0.8)
            self.set_xy(x + 4, y + 3)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(*_INK_MUTED)
            self.multi_cell(largura - 7, 3.6, _sanitize(label), align="L")
            self.set_xy(x + 4, y + altura - 11)
            self.set_font("Helvetica", "B", 13)
            self.set_text_color(*_INK_PRIMARY)
            self.cell(largura - 7, 8, _sanitize(str(valor)), align="L")
        linhas = -(-len(itens) // cols)
        self.set_y(y0 + linhas * (altura + gap))
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*_INK_PRIMARY)

    def barra_horizontal(self, label: str, valor: int, valor_max: int, indice: int = 0, color=_ROSA):
        x0, y0 = self.l_margin, self.get_y()
        altura_linha = 7
        if indice % 2 == 1:
            self.set_fill_color(*_SURFACE)
            self.rect(x0, y0, _LARGURA_CONTEUDO, altura_linha, style="F")
        self.set_xy(x0 + 2, y0 + 1.2)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*_INK_SECONDARY)
        self.cell(58, 5, _sanitize(label[:36]))
        largura_max_barra = _LARGURA_CONTEUDO - 58 - 22
        largura = (valor / valor_max * largura_max_barra) if valor_max else 0
        self.set_fill_color(*color)
        self.rect(x0 + 60, y0 + 2, max(largura, 1.2), 3.2, style="F", round_corners=True, corner_radius=1)
        self.set_xy(x0 + 60 + largura_max_barra + 3, y0 + 1.2)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*_INK_PRIMARY)
        self.cell(0, 5, str(valor))
        self.set_xy(x0, y0 + altura_linha)
        self.set_font("Helvetica", "", 10)


def _label_filtros(start: date | None, end: date | None, categoria: str | None, tipo_erro: str | None) -> str:
    partes = []
    if start or end:
        partes.append(f"Periodo: {start.isoformat() if start else '...'} a {end.isoformat() if end else '...'}")
    if categoria:
        partes.append(f"Categoria: {categoria}")
    if tipo_erro:
        partes.append(f"Tipo de erro: {tipo_erro}")
    return " | ".join(partes) if partes else "Sem filtros (todos os dados)"


def _conversa_label(conversation_id: str) -> str:
    """Limpa o identificador de conversa pra exibicao: remove o prefixo fixo
    do nome de arquivo exportado e os caracteres mangled (U+FFFD, espaco/hifen
    nao-quebravel) que aparecem em numeros de telefone extraidos do zip do
    WhatsApp - ver docs/ do historico do projeto sobre esse encoding."""
    label = conversation_id.replace("WhatsApp Chat - ", "")
    label = label.replace("�", "").replace("\xa0", " ").replace("‑", "-")
    return label.strip() or conversation_id


def _pico_heatmap(heatmap):
    if heatmap.empty or heatmap["conversas"].max() <= 0:
        return None
    linha = heatmap.loc[heatmap["conversas"].idxmax()]
    return linha["dia_semana"], linha["faixa_hora"], int(linha["conversas"])


def build_suporte_report(
    start: date | None = None,
    end: date | None = None,
    categoria: str | None = None,
    tipo_erro: str | None = None,
) -> bytes:
    with get_conn() as conn:
        df_sessions = load_sessions(conn)
        msgs_cliente = load_customer_messages(conn)
        clareza = demandas_pouco_claras(conn)
        todas_msgs = load_all_messages(conn)

    filtered = apply_suporte_filters(df_sessions, msgs_cliente, clareza, start, end, categoria, tipo_erro)
    df = filtered["df"]
    msgs_filtradas = filtered["msgs_filtradas"]
    reclamacoes_filtradas = filtered["reclamacoes_filtradas"]
    pct_pouco_clara = filtered["pct_pouco_clara"]

    pdf = Report(_label_filtros(start, end, categoria, tipo_erro))
    pdf.add_page()

    if df.empty:
        pdf.section("Sem dados")
        pdf.paragrafo("Nenhum atendimento encontrado para os filtros selecionados.")
        return bytes(pdf.output())

    sessoes_no_filtro = set(df["session_id"])
    msgs_sessoes = todas_msgs[todas_msgs["session_id"].isin(sessoes_no_filtro)]

    k = kpis(df)
    pico_serie = pico_simultaneos_por_periodo(df, "dia")["pico_simultaneos"]
    pico = int(pico_serie.max()) if not pico_serie.empty else 0
    media_hora = media_atendimentos_por_hora(df)

    total_msgs_cliente = len(msgs_filtradas)
    total_reclamacoes = len(reclamacoes_filtradas)
    pct_reclamacoes = round(total_reclamacoes / total_msgs_cliente * 100, 1) if total_msgs_cliente else 0

    # --- Resumo executivo (grid de KPIs, mesmo espirito visual dos cartoes do dashboard) ---
    pdf.section("Resumo executivo")
    tempo_medio = f"{k['tempo_resposta_medio_min']} min" if k["tempo_resposta_medio_min"] is not None else "sem dados"
    pdf.kpi_grid([
        ("Atendimentos no periodo", k["total_sessoes"], _AZUL),
        ("Tempo medio de resposta", tempo_medio, _VERDE_AGUA),
        ("Pico de atendimentos simultaneos", pico, _AMBAR),
        ("Media de atend./hora (dias uteis, 8h/dia)", media_hora, _ROXO),
        ("Demanda pouco clara", f"{pct_pouco_clara}%", _LARANJA),
        ("Reclamacoes de erro", f"{total_reclamacoes} ({pct_reclamacoes}%)", _VERMELHO),
    ])

    # --- Analise de volume (insights automaticos, sem IA - so aritmetica sobre
    # os mesmos DataFrames que alimentam os graficos do dashboard) ---
    pdf.section("Analise de volume", color=_VERDE_AGUA)
    pico_heatmap = _pico_heatmap(volume_por_dia_semana_hora(df))
    if pico_heatmap:
        dia, faixa, qtd = pico_heatmap
        pct = round(qtd / k["total_sessoes"] * 100, 1) if k["total_sessoes"] else 0
        pdf.bullet(
            f"O horario de maior concentracao de atendimentos e **{dia} entre {faixa}**, "
            f"com {qtd} atendimentos ({pct}% do total no periodo).",
            color=_VERDE_AGUA,
        )

    vol_dia = volume_atendimentos_por_periodo(df, "dia")
    msg_dia = volume_mensagens_por_periodo(msgs_sessoes, "dia")
    if not vol_dia.empty:
        merged = vol_dia.merge(msg_dia, on="periodo", how="left").fillna(0)
        merged = merged[merged["conversas"] > 0]
        if not merged.empty:
            razao_media = (merged["mensagens"] / merged["conversas"]).mean()
            pdf.bullet(
                f"Em media, cada atendimento envolve **{razao_media:.1f} mensagens** trocadas entre cliente e suporte.",
                color=_VERDE_AGUA,
            )
            if len(merged) > 1:
                corr = merged["conversas"].corr(merged["mensagens"])
                if corr == corr:  # descarta NaN (desvio-padrao zero em algum dos lados)
                    intensidade = "forte" if corr > 0.7 else "moderada" if corr > 0.4 else "fraca"
                    pdf.bullet(
                        f"Correlacao entre volume diario de atendimentos e volume de mensagens trocadas: "
                        f"**{corr:.2f} ({intensidade})**.",
                        color=_VERDE_AGUA,
                    )

    # --- Reclamacoes por tipo de erro ---
    pdf.section("Reclamacoes por tipo de erro", color=_ROSA)
    tipo_dist = distribuicao_tipo_suporte(reclamacoes_filtradas)
    if tipo_dist.empty:
        pdf.paragrafo("Nenhuma reclamacao classificada no periodo selecionado.")
    else:
        tipo_dist = tipo_dist.sort_values("mensagens", ascending=False)
        maximo = int(tipo_dist["mensagens"].max())
        for i, (_, row) in enumerate(tipo_dist.iterrows()):
            pdf.barra_horizontal(str(row["tipo"]), int(row["mensagens"]), maximo, indice=i, color=_ROSA)
        top = tipo_dist.iloc[0]
        pdf.ln(3)
        pdf.paragrafo(
            f"O tipo de erro mais frequente e '{top['tipo']}', respondendo por {int(top['mensagens'])} "
            f"das {total_reclamacoes} reclamacoes registradas."
        )

    # --- Principais temas ---
    temas = ranking_temas(df)
    if not temas.empty:
        pdf.section("Principais temas dos atendimentos", color=_ROXO)
        maximo_tema = int(temas["conversas"].max())
        for i, (_, row) in enumerate(temas.iterrows()):
            tema = row["tema"] if row["tema"] else "sem tema classificado"
            pdf.barra_horizontal(str(tema), int(row["conversas"]), maximo_tema, indice=i, color=_ROXO)

    # --- Reclamacoes com maior tempo de resposta ---
    destaque = df[df["categoria"] == "reclamacao"].sort_values("first_response_seconds", ascending=False).head(10)
    if not destaque.empty:
        pdf.section("Reclamacoes com maior tempo de resposta", color=_VERMELHO)
        for _, row in destaque.iterrows():
            tema = row["tema"] if row["tema"] else "sem tema classificado"
            tempo = row["first_response_seconds"]
            tempo_str = f"{tempo / 60:.1f} min" if tempo is not None and tempo == tempo else "sem resposta registrada"
            pdf.bullet(
                f"**[{_conversa_label(row['conversation_id'])}]** {tema} - tempo de resposta: {tempo_str}",
                color=_VERMELHO,
            )

    return bytes(pdf.output())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--categoria")
    parser.add_argument("--tipo-erro")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdf_bytes = build_suporte_report(
        start=date.fromisoformat(args.start) if args.start else None,
        end=date.fromisoformat(args.end) if args.end else None,
        categoria=args.categoria or None,
        tipo_erro=args.tipo_erro or None,
    )
    out_path = OUTPUT_DIR / f"relatorio_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.pdf"
    out_path.write_bytes(pdf_bytes)
    print(f"Relatorio gerado em {out_path}")


if __name__ == "__main__":
    main()
