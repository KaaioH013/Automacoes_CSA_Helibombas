"""E-mail: pedidos novos com margem baixa (markup < 1,40).

Uso:
  python enviar_email_margem_pedidos_novos.py
  python enviar_email_margem_pedidos_novos.py --dias 7 --enviar
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from automacoes_csa.comum import destinatarios, periodo_dias, plural
from automacoes_csa.dados import buscar_itens_pedido_margem_baixa
from automacoes_csa.email_html import montar_email_simples, secao_margem_itens
from automacoes_csa.conexao import get_engine
from automacoes_csa.email_sender import EmailConfigError, enviar_email

load_dotenv()
EXPORT_DIR = Path("exports")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Pedidos novos com markup abaixo do mínimo.")
    p.add_argument("--dias", type=int, default=7, help="Janela em dias (padrão: 7)")
    p.add_argument("--para", default=None)
    p.add_argument("--enviar", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    dt_ini, dt_fim, periodo = periodo_dias(args.dias)

    engine = get_engine()
    df = buscar_itens_pedido_margem_baixa(engine, dt_ini, dt_fim)

    corpo = secao_margem_itens(df, "pedidos", periodo, "PV", "PV")
    html = montar_email_simples(
        "Pedidos novos com margem baixa",
        periodo,
        corpo,
    )

    EXPORT_DIR.mkdir(exist_ok=True)
    slug = f"margem_pedidos_{args.dias}d"
    preview = EXPORT_DIR / f"email_{slug}.html"
    xlsx = EXPORT_DIR / f"email_{slug}.xlsx"
    preview.write_text(html, encoding="utf-8")
    if not df.empty:
        df.to_excel(xlsx, index=False)

    n = len(df)
    print(f"{n} {plural(n, 'item', 'itens')} com markup baixo em pedidos")
    print(f"Preview: {preview.resolve()}")

    if not args.enviar:
        print("Modo preview. Use --enviar para enviar.")
        return 0

    try:
        anexos = [xlsx] if xlsx.exists() else None
        enviar_email(
            destinatarios=destinatarios(args.para),
            assunto=f"[Margem] {n} {plural(n, 'item', 'itens')} em pedidos novos abaixo do markup mínimo · {periodo}",
            corpo_html=html,
            anexos=anexos,
        )
        print("Enviado.")
    except EmailConfigError as e:
        print(f"[ERRO] {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
