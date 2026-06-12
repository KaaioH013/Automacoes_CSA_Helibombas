"""Conferência de sexta — markup da semana + OBSINTERNA (cabeçalho).

Período: sexta anterior + seg a qui da semana atual.
Operadores: Caio, Priscila e Patricia.
Destino: comercial1 (Caio).

Uso:
  python conferencia_markup_sexta.py
  python conferencia_markup_sexta.py --enviar
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from automacoes_csa.comum import (
    DESTINATARIO_PADRAO,
    destinatarios,
    periodo_markup_semana_sexta,
)
from automacoes_csa.dados import (
    buscar_itens_cotacao_margem_baixa,
    buscar_itens_pedido_margem_baixa,
)
from automacoes_csa.email_html import montar_email_conferencia_markup_sexta
from automacoes_csa.conexao import get_engine
from automacoes_csa.email_sender import EmailConfigError, enviar_email

load_dotenv()
EXPORT_DIR = Path("exports")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Conferência semanal markup + OBSINTERNA (sexta).")
    p.add_argument("--para", default=None)
    p.add_argument("--enviar", action="store_true")
    p.add_argument(
        "--com-anexo",
        action="store_true",
        help="Anexa planilha Excel (padrão: só o e-mail HTML)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    engine = get_engine()

    dt_ini, dt_fim, periodo = periodo_markup_semana_sexta()
    df_cot = buscar_itens_cotacao_margem_baixa(engine, dt_ini, dt_fim)
    df_ped = buscar_itens_pedido_margem_baixa(engine, dt_ini, dt_fim)

    html = montar_email_conferencia_markup_sexta(df_cot, df_ped, periodo)

    EXPORT_DIR.mkdir(exist_ok=True)
    preview = EXPORT_DIR / "email_conferencia_markup_sexta.html"
    preview.write_text(html, encoding="utf-8")

    xlsx = EXPORT_DIR / "email_conferencia_markup_sexta.xlsx"
    with pd.ExcelWriter(xlsx, engine="openpyxl") as w:
        df_cot.to_excel(w, sheet_name="Cotacoes", index=False)
        df_ped.to_excel(w, sheet_name="Pedidos", index=False)

    n_docs_cot = df_cot["Num_Orcamento"].nunique() if not df_cot.empty else 0
    n_docs_ped = df_ped["PV"].nunique() if not df_ped.empty else 0
    sem_obs = 0
    if not df_cot.empty:
        sem_obs += sum(
            1 for _, g in df_cot.groupby("Num_Orcamento") if not g["Obs_Preenchida"].iloc[0]
        )
    if not df_ped.empty:
        sem_obs += sum(1 for _, g in df_ped.groupby("PV") if not g["Obs_Preenchida"].iloc[0])

    print(f"Conferência markup sexta — {periodo}")
    print(f"  Cotações: {n_docs_cot} docs · {len(df_cot)} itens")
    print(f"  Pedidos:  {n_docs_ped} docs · {len(df_ped)} itens")
    print(f"  Sem OBSINTERNA: {sem_obs}")
    print(f"  Preview: {preview.resolve()}")

    if not args.enviar:
        print("\nModo preview. Use --enviar para enviar.")
        return 0

    try:
        anexos = [xlsx] if args.com_anexo else None
        enviar_email(
            destinatarios=destinatarios(args.para or DESTINATARIO_PADRAO),
            assunto=f"[Conferência sexta] Markup semana · {sem_obs} sem justificativa",
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
