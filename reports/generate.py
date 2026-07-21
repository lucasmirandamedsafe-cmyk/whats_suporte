import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fpdf import FPDF

from pipeline.db import get_conn
from pipeline.metrics import distribuicao_sentimento, kpis, load_sessions, ranking_temas

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


class Report(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "Relatorio de Suporte - WhatsApp", ln=True)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
        self.set_text_color(0, 0, 0)
        self.ln(4)

    def section(self, title):
        self.set_font("Helvetica", "B", 12)
        self.ln(2)
        self.cell(0, 8, title, ln=True)
        self.set_font("Helvetica", "", 10)


def build_report(df):
    k = kpis(df)
    temas = ranking_temas(df)
    sent = distribuicao_sentimento(df)

    pdf = Report()
    pdf.add_page()

    pdf.section("Resumo executivo")
    tempo_medio = f"{k['tempo_resposta_medio_min']} min" if k["tempo_resposta_medio_min"] is not None else "sem dados"
    tempo_mediano = (
        f"{k['tempo_resposta_mediano_min']} min" if k["tempo_resposta_mediano_min"] is not None else "sem dados"
    )
    for linha in [
        f"Atendimentos no periodo: {k['total_sessoes']}",
        f"Tempo medio de resposta: {tempo_medio}",
        f"Tempo mediano de resposta: {tempo_mediano}",
        f"Reclamacoes: {k['pct_reclamacao']}%",
        f"Duvidas: {k['pct_duvida']}%",
    ]:
        pdf.cell(0, 6, linha, ln=True)

    pdf.section("Principais temas")
    for _, row in temas.iterrows():
        pdf.cell(0, 6, f"- {row['tema']}: {row['conversas']} atendimento(s)", ln=True)

    pdf.section("Sentimento dos atendimentos")
    for _, row in sent.iterrows():
        pdf.cell(0, 6, f"- {row['sentimento']}: {row['conversas']} atendimento(s)", ln=True)

    piores = df[df["categoria"] == "reclamacao"].sort_values("first_response_seconds", ascending=False).head(10)
    if not piores.empty:
        pdf.section("Reclamacoes em destaque")
        for _, row in piores.iterrows():
            resumo = (row["resumo"] or "").strip()
            pdf.multi_cell(0, 6, f"- [{row['conversation_id']}] {resumo}")

    return pdf


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        df = load_sessions(conn)

    if df.empty:
        print("Nenhum dado para gerar relatório. Rode o pipeline antes (python pipeline/run_all.py).")
        return

    pdf = build_report(df)
    out_path = OUTPUT_DIR / f"relatorio_{datetime.now().strftime('%Y-%m-%d')}.pdf"
    pdf.output(str(out_path))
    print(f"Relatório gerado em {out_path}")


if __name__ == "__main__":
    main()
