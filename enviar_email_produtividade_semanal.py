"""E-mail: produtividade semanal — inserções + tempo médio por pessoa.

Uso:
  python enviar_email_produtividade_semanal.py
  python enviar_email_produtividade_semanal.py --enviar
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from automacoes_csa.comum import destinatarios, periodo_semana_ate_hoje
from automacoes_csa.dados import buscar_produtividade_semanal
from automacoes_csa.email_html import montar_email_simples, secao_produtividade
from automacoes_csa.conexao import get_engine
from automacoes_csa.email_sender import EmailConfigError, enviar_email

load_dotenv()
EXPORT_DIR = Path("exports")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Produtividade semanal da equipe peças.")
    p.add_argument("--para", default=None)
    p.add_argument("--enviar", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    dt_ini, dt_fim, periodo = periodo_semana_ate_hoje()

    engine = get_engine()
    df = buscar_produtividade_semanal(engine, dt_ini, dt_fim)

    corpo = secao_produtividade(df, periodo)
    html = montar_email_simples("Produtividade semanal", periodo, corpo)

    EXPORT_DIR.mkdir(exist_ok=True)
    preview = EXPORT_DIR / "email_produtividade_semanal.html"
    xlsx = EXPORT_DIR / "email_produtividade_semanal.xlsx"
    preview.write_text(html, encoding="utf-8")
    df.to_excel(xlsx, index=False)

    print(f"Produtividade: {periodo}")
    print(f"Preview: {preview.resolve()}")

    if not args.enviar:
        print("Modo preview. Use --enviar para enviar.")
        return 0

    try:
        enviar_email(
            destinatarios=destinatarios(args.para),
            assunto=f"[Produtividade] Semanal peças · {periodo}",
            corpo_html=html,
            anexos=[xlsx],
        )
        print("Enviado.")
    except EmailConfigError as e:
        print(f"[ERRO] {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
