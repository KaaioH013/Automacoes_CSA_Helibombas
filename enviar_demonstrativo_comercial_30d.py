"""Envio único — demonstrativo completo dos últimos 30 dias (antes da rotina diária).

Uso:
  python enviar_demonstrativo_comercial_30d.py
  python enviar_demonstrativo_comercial_30d.py --enviar
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from automacoes_csa.comum import (
    OPERADORES_PECAS,
    email_operador,
    periodo_conferencia_pendentes,
    periodo_dias,
    periodo_mes_atual,
)
from automacoes_csa.dados import (
    buscar_cotacoes_andamento,
    buscar_itens_cotacao_margem_baixa,
    buscar_itens_pedido_margem_baixa,
    buscar_margem_mes_por_operador,
    buscar_produtividade_semanal,
)
from automacoes_csa.email_html import montar_email_rotina_manha
from automacoes_csa.conexao import get_engine
from automacoes_csa.email_sender import EmailConfigError, enviar_email

load_dotenv()
EXPORT_DIR = Path("exports")
DIAS = 30


def _intro_demonstrativo(nome: str, comercial: str, periodo: str) -> str:
    return f"""
    <p style="margin:0 0 14px;">Olá, <b>{nome}</b>,</p>
    <p style="margin:0 0 14px;font-size:15px;line-height:1.65;color:#333;">
      Este e-mail é o <b>demonstrativo completo</b> do que encontramos no <b>{periodo}</b>.
      É o panorama geral <b>antes</b> dos envios diários — a partir de <b>segunda-feira</b>,
      você passará a receber só o que for do <b>dia útil anterior</b> (bem mais enxuto).
    </p>
    <p style="margin:0 0 18px;font-size:14px;line-height:1.6;color:#555;">
      Use esta lista para <b>organizar e regularizar</b> o que ainda estiver pendente no Sectra.
      Dúvidas, responda este e-mail.
    </p>
  """


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Demonstrativo comercial 30 dias (envio único).")
    p.add_argument("--enviar", action="store_true")
    p.add_argument("--operador", choices=list(OPERADORES_PECAS.keys()), default=None)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    engine = get_engine()

    dt_ini, dt_fim, periodo = periodo_dias(DIAS)
    dt_mes_ini, dt_mes_fim, periodo_mes = periodo_mes_atual()
    dt_conf_ini, dt_conf_fim, periodo_conf = periodo_conferencia_pendentes()

    df_conf = buscar_cotacoes_andamento(engine, dt_conf_ini, dt_conf_fim)
    df_cot = buscar_itens_cotacao_margem_baixa(engine, dt_ini, dt_fim)
    df_ped = buscar_itens_pedido_margem_baixa(engine, dt_ini, dt_fim)
    df_prod = buscar_produtividade_semanal(engine, dt_ini, dt_fim)
    df_margem = buscar_margem_mes_por_operador(engine, dt_mes_ini, dt_mes_fim)

    operadores = [args.operador] if args.operador else list(OPERADORES_PECAS.keys())
    EXPORT_DIR.mkdir(exist_ok=True)

    for erp in operadores:
        op = OPERADORES_PECAS[erp]

        def _filtrar(df: pd.DataFrame) -> pd.DataFrame:
            if df.empty or "Operador" not in df.columns:
                return df.iloc[0:0].copy()
            return df[df["Operador"].astype(str).str.upper() == erp].copy()

        df_conf_o = _filtrar(df_conf)
        df_cot_o = _filtrar(df_cot)
        df_ped_o = _filtrar(df_ped)
        df_prod_o = _filtrar(df_prod)
        df_margem_o = _filtrar(df_margem)

        html = montar_email_rotina_manha(
            periodo_semana=periodo,
            periodo_mes=periodo_mes,
            periodo_conferencia=periodo_conf,
            df_conferencia=df_conf_o,
            df_cot_margem=df_cot_o,
            df_ped_margem=df_ped_o,
            df_prod=df_prod_o,
            df_margem_mes=df_margem_o,
            periodo_markup=periodo,
            operador_erp=erp,
            intro_html=_intro_demonstrativo(op.nome, op.comercial, periodo),
            incluir_guia=False,
            titulo=f"Demonstrativo comercial — {op.nome}",
            subtitulo=f"{periodo} · {datetime.now().strftime('%d/%m/%Y')}",
        )

        slug = f"demonstrativo_{erp.lower()}"
        preview = EXPORT_DIR / f"email_{slug}.html"
        preview.write_text(html, encoding="utf-8")

        print(f"\n--- {op.nome} ({op.comercial}) ---")
        print(f"  Conferência: {len(df_conf_o)} | Cot. margem: {len(df_cot_o)} | Ped. margem: {len(df_ped_o)}")
        print(f"  Preview: {preview.resolve()}")

        if not args.enviar:
            continue

        try:
            enviar_email(
                destinatarios=[email_operador(erp)],
                assunto=f"[Demonstrativo] {op.nome} · últimos {DIAS} dias",
                corpo_html=html,
            )
            print(f"  Enviado para: {email_operador(erp)}")
        except EmailConfigError as e:
            print(f"  [ERRO] {e}")
            return 1

    if not args.enviar:
        print("\nModo preview. Use --enviar para enviar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
