"""E-mail: margem do mês por operador interno (resumo fase3_margens).

Uso:
  python enviar_email_margem_mes_operador.py
  python enviar_email_margem_mes_operador.py --enviar
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from automacoes_csa.comum import destinatarios, periodo_mes_atual
from automacoes_csa.dados import buscar_margem_mes_por_operador
from automacoes_csa.email_html import montar_email_simples, secao_margem_mes
from automacoes_csa.conexao import get_engine
from automacoes_csa.email_sender import EmailConfigError, enviar_email

load_dotenv()
EXPORT_DIR = Path("exports")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Margem do mês por operador (quem inseriu).")
    p.add_argument("--para", default=None)
    p.add_argument("--enviar", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    dt_ini, dt_fim, periodo = periodo_mes_atual()

    engine = get_engine()
    df = buscar_margem_mes_por_operador(engine, dt_ini, dt_fim)

    corpo = secao_margem_mes(df, periodo)
    html = montar_email_simples("Margem do mês por operador", periodo, corpo)

    EXPORT_DIR.mkdir(exist_ok=True)
    preview = EXPORT_DIR / "email_margem_mes_operador.html"
    xlsx = EXPORT_DIR / "email_margem_mes_operador.xlsx"
    preview.write_text(html, encoding="utf-8")
    df.to_excel(xlsx, index=False)

    print(f"Margem mês: {periodo}")
    print(f"Preview: {preview.resolve()}")

    if not args.enviar:
        print("Modo preview. Use --enviar para enviar.")
        return 0

    try:
        enviar_email(
            destinatarios=destinatarios(args.para),
            assunto=f"[Margem] Resumo do mês por operador · {periodo}",
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
