"""E-mail de conferência — cotações em andamento (status A) sem envio registrado.

Operadores peças (INSERTNAME Sectra):
  CAIOSANTANA     → Caio      (Comercial 1)
  PRISCILASANTORO → Priscila  (Comercial 6)
  PATRICIA        → Patricia  (Comercial 4)

Envio: sempre para comercial1@helibombas.com.br (ou ALERTAS_EMAIL_TO), por enquanto.

Uso:
  python enviar_email_conferencia_cotacoes.py --usuario PRISCILASANTORO
  python enviar_email_conferencia_cotacoes.py --todos --mes-ini 2026-04 --mes-fim 2026-05 --enviar
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from automacoes_csa.conexao import get_engine
from automacoes_csa.email_sender import EmailConfigError, enviar_email

load_dotenv()
EXPORT_DIR = Path("exports")
DESTINATARIO_PADRAO = "comercial1@helibombas.com.br"
MARCA_CSA = "CSA®"


@dataclass(frozen=True)
class Operador:
    erp: str
    nome: str
    comercial: str


OPERADORES: dict[str, Operador] = {
    "CAIOSANTANA": Operador("CAIOSANTANA", "Caio", "Comercial 1"),
    "PRISCILASANTORO": Operador("PRISCILASANTORO", "Priscila", "Comercial 6"),
    "PATRICIA": Operador("PATRICIA", "Patricia", "Comercial 4"),
}


def _plural(n: int, singular: str, plural: str) -> str:
    return singular if n == 1 else plural


def _periodo_label(mes_ini: str, mes_fim: str) -> str:
    if mes_ini == mes_fim:
        y, m = mes_ini.split("-")
        meses = (
            "janeiro", "fevereiro", "março", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
        )
        return f"{meses[int(m) - 1]} de {y}"
    return f"{mes_ini} a {mes_fim}"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="E-mail de conferência de cotações em andamento (status A).")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--usuario", choices=list(OPERADORES.keys()), help="INSERTNAME no Sectra")
    g.add_argument("--todos", action="store_true", help="Gera/envia para os 3 operadores de peças")
    p.add_argument("--mes-ini", default="2026-04")
    p.add_argument("--mes-fim", default="2026-05")
    p.add_argument("--para", default=None, help="Destinatário (padrão: comercial1)")
    p.add_argument("--cc", default=None)
    p.add_argument("--enviar", action="store_true")
    p.add_argument("--sem-anexo", action="store_true", help="Não anexa a planilha Excel")
    return p.parse_args()


def _periodo_bounds(mes_ini: str, mes_fim: str) -> tuple[str, str]:
    y1, m1 = map(int, mes_ini.split("-"))
    y2, m2 = map(int, mes_fim.split("-"))
    dt_ini = f"{y1}-{m1:02d}-01"
    dt_fim = f"{y2 + 1}-01-01" if m2 == 12 else f"{y2}-{m2 + 1:02d}-01"
    return dt_ini, dt_fim


def buscar_cotacoes_andamento(engine, usuario: str, dt_ini: str, dt_fim: str) -> pd.DataFrame:
    usuario_sql = usuario.replace("'", "''")
    sql = f"""
    SELECT
        o.NUMERO AS Num_Orcamento,
        o.CODIGO AS Cod_Orcamento,
        FORMAT(o.DTCADASTRO, 'yyyy-MM') AS Mes,
        o.INSERTDATE,
        o.DTVALIDADE,
        ISNULL(o.VLRORCADO, 0) AS Vlr_Orcado,
        f.RAZAO AS Cliente
    FROM VE_ORCAMENTOS o
    LEFT JOIN FN_FORNECEDORES f ON f.CODIGO = o.CODCLIENTE
    WHERE o.DTCADASTRO >= '{dt_ini}'
      AND o.DTCADASTRO <  '{dt_fim}'
      AND o.FILIAL IN (1, 2)
      AND o.STATUS = 'A'
      AND UPPER(LTRIM(RTRIM(ISNULL(o.INSERTNAME, '')))) = '{usuario_sql.upper()}'
      AND (
          o.DTENVIO IS NULL
          OR (
              DATEPART(HOUR, o.DTENVIO) = 0
              AND DATEPART(MINUTE, o.DTENVIO) = 0
              AND DATEPART(SECOND, o.DTENVIO) = 0
          )
      )
    ORDER BY o.INSERTDATE, o.NUMERO
    """
    df = pd.read_sql(sql, engine)
    if df.empty:
        return df
    df["InsertDate"] = pd.to_datetime(df["INSERTDATE"], errors="coerce")
    df["DtValidade"] = pd.to_datetime(df["DTVALIDADE"], errors="coerce")
    hoje = pd.Timestamp.now().normalize()
    df["Validade_Vencida"] = df["DtValidade"].notna() & (df["DtValidade"] < hoje)
    return df


def _fmt_brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_data(v) -> str:
    if pd.isna(v):
        return "—"
    return pd.to_datetime(v).strftime("%d/%m/%Y")


def montar_html(df: pd.DataFrame, op: Operador, mes_ini: str, mes_fim: str) -> str:
    n = len(df)
    periodo = _periodo_label(mes_ini, mes_fim)
    cotacao_txt = _plural(n, "cotação", "cotações")
    identificada_txt = _plural(n, "identificada", "identificadas")
    inserida_txt = _plural(n, "inserida", "inseridas")
    pendente_txt = _plural(n, "pendente", "pendentes")
    vencida_txt = _plural(int(df["Validade_Vencida"].sum()) if not df.empty else 0, "vencida", "vencidas")

    linhas = ""
    for i, r in df.iterrows():
        zebra = "#ffffff" if i % 2 == 0 else "#f8faf9"
        badge = (
            '<span style="background:#fde8e8;color:#a33;padding:2px 8px;border-radius:4px;font-size:11px;">Vencida</span>'
            if r["Validade_Vencida"]
            else '<span style="background:#e8f5ec;color:#2d5c38;padding:2px 8px;border-radius:4px;font-size:11px;">No prazo</span>'
        )
        cliente = str(r["Cliente"]) if pd.notna(r["Cliente"]) else "—"
        if len(cliente) > 50:
            cliente = cliente[:50] + "…"
        linhas += f"""
        <tr style="background:{zebra};">
          <td style="padding:10px 12px;border-bottom:1px solid #e8eee9;font-weight:600;">{r['Num_Orcamento']}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e8eee9;">{_fmt_data(r['InsertDate'])}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e8eee9;">{_fmt_data(r['DtValidade'])}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e8eee9;">{badge}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e8eee9;text-align:right;white-space:nowrap;">{_fmt_brl(float(r['Vlr_Orcado']))}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e8eee9;">{cliente}</td>
        </tr>"""

    tabela_corpo = (
        linhas
        if linhas
        else '<tr><td colspan="6" style="padding:20px;text-align:center;color:#666;">Nenhuma cotação em andamento para conferir neste período.</td></tr>'
    )

    nums = ", ".join(df["Num_Orcamento"].astype(str).tolist()) if n else "—"
    resumo_vencidas = ""
    if not df.empty and df["Validade_Vencida"].any():
        nv = int(df["Validade_Vencida"].sum())
        resumo_vencidas = (
            f'<p style="margin:12px 0 0;color:#a33;font-size:14px;">'
            f"⚠ {nv} {_plural(nv, 'cotação com validade vencida', 'cotações com validade vencida')}."
            f"</p>"
        )

    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#eef2ef;font-family:'Segoe UI',Calibri,Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#eef2ef;padding:24px 12px;">
    <tr><td align="center">
      <table role="presentation" width="640" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">

        <tr><td style="background:#3B7A4A;padding:20px 28px;">
          <div style="color:#fff;font-size:11px;letter-spacing:.5px;text-transform:uppercase;opacity:.9;">Helibombas · Peças</div>
          <div style="color:#fff;font-size:20px;font-weight:600;margin-top:4px;">Conferência de cotações em andamento</div>
          <div style="color:#d4ead9;font-size:13px;margin-top:6px;">{op.comercial} · {op.nome} · {periodo}</div>
        </td></tr>

        <tr><td style="padding:28px;color:#333;font-size:15px;line-height:1.55;">
          <p style="margin:0 0 16px;">Olá, <b>{op.nome}</b>,</p>

          <p style="margin:0 0 16px;">
            {_plural(n, 'Foi identificada', 'Foram identificadas')} <b>{n} {cotacao_txt}</b>
            {inserida_txt} por você em <b>{periodo}</b> que ainda estão <b>em andamento</b>
            e <b>não constam como enviadas</b> no sistema.
          </p>

          <p style="margin:0 0 20px;">Para cada uma, favor conferir:</p>

          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
            <tr>
              <td style="padding:14px 16px;background:#f4f7f5;border-left:4px solid #3B7A4A;border-radius:0 6px 6px 0;">
                <div style="font-size:14px;line-height:1.7;">
                  <div>① A cotação <b>ainda é válida</b> para o cliente?</div>
                  <div>② Se sim → <b>marcar como enviada</b> no Sectra.</div>
                  <div>③ Se não → <b>marcar como perdida</b>.</div>
                </div>
              </td>
            </tr>
          </table>

          <div style="background:#f8faf9;border:1px solid #e0e8e2;border-radius:6px;padding:14px 16px;margin-bottom:20px;">
            <div style="font-size:13px;color:#555;margin-bottom:6px;">Resumo</div>
            <div style="font-size:15px;"><b>{n}</b> {cotacao_txt} {pendente_txt} de conferência</div>
            <div style="font-size:13px;color:#555;margin-top:8px;word-break:break-word;"><b>Números:</b> {nums}</div>
            {resumo_vencidas}
          </div>

          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e0e8e2;border-radius:6px;overflow:hidden;font-size:13px;">
            <thead>
              <tr style="background:#2d5c38;color:#fff;">
                <th style="padding:10px 12px;text-align:left;font-weight:600;">Cotação</th>
                <th style="padding:10px 12px;text-align:left;font-weight:600;">Inclusão</th>
                <th style="padding:10px 12px;text-align:left;font-weight:600;">Validade</th>
                <th style="padding:10px 12px;text-align:left;font-weight:600;">Situação</th>
                <th style="padding:10px 12px;text-align:right;font-weight:600;">Valor</th>
                <th style="padding:10px 12px;text-align:left;font-weight:600;">Cliente</th>
              </tr>
            </thead>
            <tbody>{tabela_corpo}</tbody>
          </table>

          <p style="margin:24px 0 0;font-size:13px;color:#777;">
            Qualquer dúvida, responda este e-mail.<br>
            Gerado em {datetime.now().strftime("%d/%m/%Y às %H:%M")}.
          </p>
        </td></tr>

        <tr><td style="background:#f4f7f5;padding:14px 28px;font-size:11px;color:#888;text-align:center;line-height:1.6;">
          Conferência interna · Equipe comercial peças<br>
          <span style="color:#aaa;">Desenvolvido por {MARCA_CSA}</span>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body></html>"""


def processar_operador(
    engine,
    op: Operador,
    mes_ini: str,
    mes_fim: str,
    enviar: bool,
    para: str | None,
    cc: str | None,
    sem_anexo: bool = False,
) -> None:
    dt_ini, dt_fim = _periodo_bounds(mes_ini, mes_fim)
    df = buscar_cotacoes_andamento(engine, op.erp, dt_ini, dt_fim)
    html = montar_html(df, op, mes_ini, mes_fim)

    slug = f"{op.erp.lower()}_{mes_ini.replace('-', '')}_{mes_fim.replace('-', '')}"
    preview_path = EXPORT_DIR / f"email_conferencia_{slug}.html"
    xlsx_path = EXPORT_DIR / f"email_conferencia_{slug}.xlsx"

    EXPORT_DIR.mkdir(exist_ok=True)
    preview_path.write_text(html, encoding="utf-8")
    if not df.empty:
        export = df[
            ["Num_Orcamento", "Mes", "InsertDate", "DtValidade", "Validade_Vencida", "Vlr_Orcado", "Cliente"]
        ].copy()
        export.to_excel(xlsx_path, index=False)

    n = len(df)
    print(f"\n[{op.comercial} - {op.nome}] {n} {_plural(n, 'cotacao', 'cotacoes')} status A")
    print(f"  Preview: {preview_path.resolve()}")
    if not df.empty:
        print(f"  Excel:   {xlsx_path.resolve()}")

    if not enviar:
        return

    destinatarios = [
        e.strip()
        for e in (para or os.getenv("ALERTAS_EMAIL_TO") or DESTINATARIO_PADRAO).split(",")
        if e.strip()
    ]
    cc_list = [e.strip() for e in (cc or os.getenv("ALERTAS_EMAIL_CC") or "").split(",") if e.strip()]
    periodo = _periodo_label(mes_ini, mes_fim)
    n = len(df)
    assunto = (
        f"[Conferência] {n} {_plural(n, 'cotação', 'cotações')} em andamento — "
        f"{op.nome} ({op.comercial}) · {periodo}"
    )

    anexos = None
    if not sem_anexo and xlsx_path.exists():
        anexos = [xlsx_path]

    enviar_email(
        destinatarios=destinatarios,
        assunto=assunto,
        corpo_html=html,
        anexos=anexos,
        cc=cc_list or None,
    )
    print(f"  Enviado para: {', '.join(destinatarios)}")


def main() -> int:
    args = parse_args()
    usuarios = list(OPERADORES.keys()) if args.todos else [args.usuario or "PRISCILASANTORO"]

    engine = get_engine()
    try:
        for erp in usuarios:
            processar_operador(
                engine,
                OPERADORES[erp],
                args.mes_ini,
                args.mes_fim,
                args.enviar,
                args.para,
                args.cc,
                sem_anexo=args.sem_anexo,
            )
    except EmailConfigError as e:
        print(f"\n[ERRO] {e}")
        return 1

    if not args.enviar:
        print("\nModo preview. Use --enviar para enviar (destino padrão: comercial1).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
