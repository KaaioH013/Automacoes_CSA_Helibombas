"""Rotina comercial manhã — e-mail diário por operador (peças).

Uso:
  python rotina_comercial_manha.py
  python rotina_comercial_manha.py --enviar-equipe          # envia para Caio, Priscila e Patricia
  python rotina_comercial_manha.py --operador PRISCILASANTORO --enviar
  python rotina_comercial_manha.py --preview-equipe --enviar  # 3 e-mails só para Caio
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from automacoes_csa.comum import (
    DESTINATARIO_PADRAO,
    OPERADORES_PECAS,
    destinatarios,
    email_operador,
    periodo_conferencia_pendentes,
    periodo_markup_dia_util_anterior,
    periodo_mes_atual,
    periodo_semana_ate_hoje,
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

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Rotina comercial manhã — e-mail por operador.")
    p.add_argument("--para", default=None)
    p.add_argument("--enviar", action="store_true")
    p.add_argument(
        "--com-anexo",
        action="store_true",
        help="Anexa planilha Excel (padrão: só o e-mail HTML)",
    )
    p.add_argument(
        "--operador",
        choices=list(OPERADORES_PECAS.keys()),
        default=None,
        help="Gera/envia só uma pessoa (ex: PRISCILASANTORO)",
    )
    p.add_argument(
        "--preview-equipe",
        action="store_true",
        help=f"Envia um e-mail de cada operador só para você ({DESTINATARIO_PADRAO})",
    )
    p.add_argument(
        "--enviar-equipe",
        action="store_true",
        help="Envia um e-mail completo para cada operador no e-mail dele",
    )
    return p.parse_args()


def _filtrar_df_operador(df: pd.DataFrame, erp: str) -> pd.DataFrame:
    if df.empty or "Operador" not in df.columns:
        return df.iloc[0:0].copy()
    return df[df["Operador"].astype(str).str.upper() == erp.upper()].copy()


def _gerar_rotina_operador(
    erp: str,
    df_conf: pd.DataFrame,
    df_cot: pd.DataFrame,
    df_ped: pd.DataFrame,
    df_prod: pd.DataFrame,
    df_margem: pd.DataFrame,
    periodo_sem: str,
    periodo_mes: str,
    periodo_conf: str,
    periodo_markup: str,
) -> tuple[str, Path, Path]:
    df_conf_o = _filtrar_df_operador(df_conf, erp)
    df_cot_o = _filtrar_df_operador(df_cot, erp)
    df_ped_o = _filtrar_df_operador(df_ped, erp)
    df_prod_o = _filtrar_df_operador(df_prod, erp)
    df_margem_o = _filtrar_df_operador(df_margem, erp)

    html = montar_email_rotina_manha(
        periodo_semana=periodo_sem,
        periodo_mes=periodo_mes,
        periodo_conferencia=periodo_conf,
        df_conferencia=df_conf_o,
        df_cot_margem=df_cot_o,
        df_ped_margem=df_ped_o,
        df_prod=df_prod_o,
        df_margem_mes=df_margem_o,
        periodo_markup=periodo_markup,
        operador_erp=erp,
    )

    EXPORT_DIR.mkdir(exist_ok=True)
    slug = erp.lower()
    preview = EXPORT_DIR / f"email_rotina_{slug}.html"
    preview.write_text(html, encoding="utf-8")

    xlsx_path = EXPORT_DIR / f"email_rotina_{slug}.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as w:
        df_conf_o.to_excel(w, sheet_name="Conferencia", index=False)
        df_cot_o.to_excel(w, sheet_name="Cot_Margem_Baixa", index=False)
        df_ped_o.to_excel(w, sheet_name="Ped_Margem_Baixa", index=False)
        df_prod_o.to_excel(w, sheet_name="Produtividade", index=False)
        df_margem_o.to_excel(w, sheet_name="Margem_Mes", index=False)

    return html, preview, xlsx_path


def main() -> int:
    args = parse_args()
    if args.enviar_equipe and not args.preview_equipe:
        args.enviar = True
    modos = sum(bool(x) for x in (args.preview_equipe, args.enviar_equipe, args.operador))
    if modos > 1:
        print("[ERRO] Use apenas um: --preview-equipe, --enviar-equipe ou --operador.")
        return 1

    engine = get_engine()

    dt_sem_ini, dt_sem_fim, periodo_sem = periodo_semana_ate_hoje()
    dt_mes_ini, dt_mes_fim, periodo_mes = periodo_mes_atual()
    dt_conf_ini, dt_conf_fim, periodo_conf = periodo_conferencia_pendentes()
    dt_mk_ini, dt_mk_fim, periodo_markup = periodo_markup_dia_util_anterior()

    df_conf = buscar_cotacoes_andamento(engine, dt_conf_ini, dt_conf_fim)
    df_cot = buscar_itens_cotacao_margem_baixa(engine, dt_mk_ini, dt_mk_fim)
    df_ped = buscar_itens_pedido_margem_baixa(engine, dt_mk_ini, dt_mk_fim)
    df_prod = buscar_produtividade_semanal(engine, dt_sem_ini, dt_sem_fim)
    df_margem = buscar_margem_mes_por_operador(engine, dt_mes_ini, dt_mes_fim)

    operadores = (
        list(OPERADORES_PECAS.keys())
        if args.preview_equipe or args.enviar_equipe
        else [args.operador] if args.operador
        else [None]
    )

    dest_preview = destinatarios(args.para or DESTINATARIO_PADRAO)

    for erp in operadores:
        if erp is None:
            html = montar_email_rotina_manha(
                periodo_semana=periodo_sem,
                periodo_mes=periodo_mes,
                periodo_conferencia=periodo_conf,
                df_conferencia=df_conf,
                df_cot_margem=df_cot,
                df_ped_margem=df_ped,
                df_prod=df_prod,
                df_margem_mes=df_margem,
                periodo_markup=periodo_markup,
                operador_erp=None,
            )
            slug = "comercial_manha"
            preview = EXPORT_DIR / f"email_rotina_{slug}.html"
            preview.write_text(html, encoding="utf-8")
            xlsx_path = EXPORT_DIR / f"email_rotina_{slug}.xlsx"
            with pd.ExcelWriter(xlsx_path, engine="openpyxl") as w:
                df_conf.to_excel(w, sheet_name="Conferencia", index=False)
                df_cot.to_excel(w, sheet_name="Cot_Margem_Baixa", index=False)
                df_ped.to_excel(w, sheet_name="Ped_Margem_Baixa", index=False)
                df_prod.to_excel(w, sheet_name="Produtividade", index=False)
                df_margem.to_excel(w, sheet_name="Margem_Mes", index=False)
            nome_op = None
        else:
            html, preview, xlsx_path = _gerar_rotina_operador(
                erp, df_conf, df_cot, df_ped, df_prod, df_margem,
                periodo_sem, periodo_mes, periodo_conf, periodo_markup,
            )
            op = OPERADORES_PECAS[erp]
            nome_op = op.nome
            df_conf_o = _filtrar_df_operador(df_conf, erp)
            df_cot_o = _filtrar_df_operador(df_cot, erp)
            df_ped_o = _filtrar_df_operador(df_ped, erp)
            print(f"\n--- {nome_op} ({op.comercial}) ---")
            print(f"  Conferência: {len(df_conf_o)} | Cot. margem: {len(df_cot_o)} | Ped. margem: {len(df_ped_o)}")
            print(f"  Preview: {preview.resolve()}")

        if not args.enviar:
            continue

        try:
            prefixo = "[PREVIEW] " if args.preview_equipe else ""
            assunto = (
                f"{prefixo}[Rotina manhã] {nome_op} · {periodo_sem}"
                if nome_op
                else f"{prefixo}[Rotina manhã] Comercial peças · {periodo_sem}"
            )
            if args.preview_equipe:
                para = dest_preview
            elif args.enviar_equipe:
                para = [email_operador(erp)]
            else:
                para = destinatarios(args.para)
            anexos = [xlsx_path] if args.com_anexo else None
            enviar_email(
                destinatarios=para,
                assunto=assunto,
                corpo_html=html,
                anexos=anexos,
            )
            print(f"  Enviado para: {', '.join(para)}")
        except EmailConfigError as e:
            print(f"  [ERRO] {e}")
            return 1

    if not args.enviar:
        print("\nModo preview. Use --enviar para enviar.")
        if args.preview_equipe:
            print(f"  Preview equipe: 3 e-mails para {DESTINATARIO_PADRAO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
