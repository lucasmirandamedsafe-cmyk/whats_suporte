"""CLI que imprime em JSON (stdout) os dados do dashboard - chamado pelas rotas
de API do Next.js (web/src/lib/pythonBridge.ts) via subprocess, um processo por
requisicao. Substitui o antigo servidor FastAPI: nao ha processo Python de
longa duracao rodando - cada chamada le data/whatsapp.db, calcula via
pipeline/metrics.py e termina.

Uso:
    python -m api.cli suporte-filtros
    python -m api.cli suporte-dashboard --start 2026-01-01 --end 2026-02-01 \
        --categoria reclamacao --tipo-erro acesso_login
    python -m api.cli grupos-filtros
    python -m api.cli grupos-dashboard --areas saude --areas educacao --start ... --end ...
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.dashboard_data import grupos_dashboard, grupos_filtros, suporte_dashboard, suporte_filtros


def _parse_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="api.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("suporte-filtros")

    p_suporte = subparsers.add_parser("suporte-dashboard")
    p_suporte.add_argument("--start")
    p_suporte.add_argument("--end")
    p_suporte.add_argument("--categoria")
    p_suporte.add_argument("--tipo-erro")

    subparsers.add_parser("grupos-filtros")

    p_grupos = subparsers.add_parser("grupos-dashboard")
    p_grupos.add_argument("--areas", action="append")
    p_grupos.add_argument("--start")
    p_grupos.add_argument("--end")

    args = parser.parse_args(argv)

    if args.command == "suporte-filtros":
        result = suporte_filtros()
    elif args.command == "suporte-dashboard":
        result = suporte_dashboard(
            start=_parse_date(args.start),
            end=_parse_date(args.end),
            categoria=args.categoria or None,
            tipo_erro=args.tipo_erro or None,
        )
    elif args.command == "grupos-filtros":
        result = grupos_filtros()
    elif args.command == "grupos-dashboard":
        result = grupos_dashboard(
            areas=args.areas or None,
            start=_parse_date(args.start),
            end=_parse_date(args.end),
        )
    else:  # pragma: no cover - argparse ja restringe as opcoes validas
        parser.error(f"comando desconhecido: {args.command}")
        return

    sys.stdout.write(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
