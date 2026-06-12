"""Templates HTML e-mail — padrão Helibombas + CSA®."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from automacoes_csa.comum import (
    MARCA_CSA,
    MARKUP_MINIMO,
    NOME_SISTEMA,
    OPERADORES_PECAS,
    Operador,
    fmt_brl,
    fmt_data,
    fmt_markup,
    fmt_pct,
    plural,
)


def _zebra(i: int) -> str:
    return "#ffffff" if i % 2 == 0 else "#f8faf9"


def _secao_titulo(titulo: str, subtitulo: str = "") -> str:
    sub = f'<div style="color:#d4ead9;font-size:13px;margin-top:6px;">{subtitulo}</div>' if subtitulo else ""
    return f"""
    <tr><td style="background:#3B7A4A;padding:20px 28px;">
      <div style="color:#fff;font-size:11px;letter-spacing:.5px;text-transform:uppercase;opacity:.9;">Helibombas · Peças</div>
      <div style="color:#fff;font-size:20px;font-weight:600;margin-top:4px;">{titulo}</div>
      {sub}
    </td></tr>"""


def _bloco_secao(titulo: str, corpo: str, id_sec: str = "") -> str:
    anc = f'id="{id_sec}"' if id_sec else ""
    return f"""
    <div {anc} style="margin-top:32px;">
      <h2 style="margin:0 0 12px;font-size:17px;color:#2d5c38;border-bottom:2px solid #3B7A4A;padding-bottom:8px;">{titulo}</h2>
      {corpo}
    </div>"""


def _tabela(headers: list[str], linhas: str, alinhamentos: list[str] | None = None) -> str:
    alin = alinhamentos or ["left"] * len(headers)
    ths = "".join(
        f'<th style="padding:10px 12px;text-align:{a};font-weight:600;">{h}</th>'
        for h, a in zip(headers, alin)
    )
    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="border:1px solid #e0e8e2;border-radius:6px;overflow:hidden;font-size:13px;">
      <thead><tr style="background:#2d5c38;color:#fff;">{ths}</tr></thead>
      <tbody>{linhas}</tbody>
    </table>"""


def _vazio(colspan: int, msg: str) -> str:
    return f'<tr><td colspan="{colspan}" style="padding:20px;text-align:center;color:#666;">{msg}</td></tr>'


def _esc_html(texto: str) -> str:
    return (
        str(texto or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _fmt_doc_id(val) -> str:
    if isinstance(val, float) and val == int(val):
        return str(int(val))
    return str(val)


def _linha_item_margem(i: int, r: pd.Series) -> str:
    desc = _esc_html(str(r.get("Descricao", "") or "").strip())
    mat = _esc_html(str(r.get("Material", "")))
    if not desc:
        item_txt = mat
    else:
        item_txt = f"{desc}<br><span style='color:#888;font-size:11px;'>{mat}</span>"
    return f"""
        <tr style="background:{_zebra(i)};">
          <td style="padding:8px 12px;border-bottom:1px solid #e8eee9;">{item_txt}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e8eee9;text-align:right;color:#a33;font-weight:600;">{fmt_markup(float(r['Markup']))}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e8eee9;text-align:right;">{fmt_pct(float(r['Margem_pct']))}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e8eee9;text-align:right;">{fmt_brl(float(r['Vlr_Unit_Venda']))}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e8eee9;text-align:right;">{fmt_brl(float(r['Vlr_Custo']))}</td>
        </tr>"""


def _lista_margem_agrupada(
    df: pd.DataFrame,
    doc_col: str,
    doc_titulo: str,
    vazio_msg: str,
    max_itens: int = 50,
) -> str:
    """Agrupa por cotação ou PV: cabeçalho com cliente, itens abaixo."""
    if df.empty:
        return f'<p style="color:#666;font-size:13px;margin:0;">{vazio_msg}</p>'

    partes: list[str] = []
    itens_mostrados = 0
    docs_mostrados = 0
    max_docs = 20

    for doc_id, grp in df.groupby(doc_col, sort=False):
        if itens_mostrados >= max_itens or docs_mostrados >= max_docs:
            break

        cliente = _esc_html(str(grp["Cliente"].iloc[0]) if "Cliente" in grp.columns else "—")
        if len(cliente) > 60:
            cliente = cliente[:60] + "…"

        cabecalho = f"""
        <div style="margin:18px 0 0;padding:12px 14px;background:#f4f7f5;border-left:4px solid #c45a11;border-radius:0 6px 6px 0;">
          <div style="font-size:15px;font-weight:600;color:#2d5c38;">{doc_titulo} {_esc_html(_fmt_doc_id(doc_id))}</div>
          <div style="font-size:13px;color:#555;margin-top:4px;">{cliente}</div>
        </div>"""

        linhas = ""
        for j, (_, r) in enumerate(grp.iterrows()):
            if itens_mostrados >= max_itens:
                break
            linhas += _linha_item_margem(j, r)
            itens_mostrados += 1

        if linhas:
            partes.append(
                cabecalho
                + _tabela(
                    ["Item", "Markup", "Margem", "Venda", "Custo"],
                    linhas,
                    ["left", "right", "right", "right", "right"],
                )
            )
            docs_mostrados += 1

    restantes = len(df) - itens_mostrados
    if restantes > 0:
        partes.append(
            f'<p style="font-size:12px;color:#777;margin-top:12px;">+ {restantes} itens na planilha anexa.</p>'
        )

    return "".join(partes)


def secao_margem_itens(
    df: pd.DataFrame,
    tipo: str,
    periodo: str,
    doc_col: str,
    doc_label: str,
) -> str:
    n = len(df)
    n_docs = df[doc_col].nunique() if not df.empty else 0
    intro = (
        f"<p style='margin:0 0 16px;'>"
        f"<b>{n_docs}</b> {plural(n_docs, doc_label.lower(), doc_label.lower() + 's')} · "
        f"<b>{n}</b> {plural(n, 'item', 'itens')} com markup &lt; <b>{MARKUP_MINIMO:.2f}</b> "
        f"(custo unit. ≥ R$ 5,00) em <b>{periodo}</b>."
        f"</p>"
    )
    corpo = _lista_margem_agrupada(
        df,
        doc_col,
        doc_label,
        f"Nenhum item com margem baixa em {tipo.lower()} neste período.",
    )
    return intro + corpo


def secao_produtividade(df: pd.DataFrame, periodo: str) -> str:
    intro = (
        f"<p style='margin:0 0 16px;'>Inserções e tempo médio cotação→envio (sessão 8h) — <b>{periodo}</b>.</p>"
    )
    if df.empty:
        return intro + _tabela(
            ["Operador", "Cotações", "Pedidos", "Com envio", "Tempo médio"],
            _vazio(5, "Sem dados no período."),
            ["left", "right", "right", "right", "right"],
        )

    linhas = ""
    for i, r in df.iterrows():
        linhas += f"""
        <tr style="background:{_zebra(i)};">
          <td style="padding:10px 12px;border-bottom:1px solid #e8eee9;"><b>{r['Nome']}</b> <span style="color:#888;">({r['Comercial']})</span></td>
          <td style="padding:10px 12px;border-bottom:1px solid #e8eee9;text-align:right;">{int(r['Cotacoes'])}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e8eee9;text-align:right;">{int(r['Pedidos'])}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e8eee9;text-align:right;">{int(r['Com_Envio'])}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e8eee9;text-align:right;">{r['Tempo_Medio_Fmt']}</td>
        </tr>"""

    return intro + _tabela(
        ["Operador", "Cotações", "Pedidos", "Com envio", "Tempo médio"],
        linhas,
        ["left", "right", "right", "right", "right"],
    )


def secao_margem_mes(df: pd.DataFrame, periodo: str) -> str:
    intro = (
        f"<p style='margin:0 0 16px;'>Resumo de margem em pedidos (fase3) por quem inseriu — <b>{periodo}</b>. "
        f"Markup mínimo: <b>{MARKUP_MINIMO:.2f}</b>.</p>"
    )
    if df.empty:
        return intro + _tabela(
            ["Operador", "Pedidos", "Itens", "Faturamento", "Margem média", "Markup médio", "Itens abaixo"],
            _vazio(7, "Sem pedidos no mês."),
            ["left", "right", "right", "right", "right", "right", "right"],
        )

    linhas = ""
    for i, r in df.iterrows():
        alerta = int(r.get("Itens_Markup_Baixo", 0))
        badge = (
            f'<span style="background:#fde8e8;color:#a33;padding:2px 8px;border-radius:4px;">{alerta}</span>'
            if alerta else "0"
        )
        linhas += f"""
        <tr style="background:{_zebra(i)};">
          <td style="padding:10px 12px;border-bottom:1px solid #e8eee9;"><b>{r['Nome']}</b> <span style="color:#888;">({r['Comercial']})</span></td>
          <td style="padding:10px 12px;border-bottom:1px solid #e8eee9;text-align:right;">{int(r['Pedidos'])}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e8eee9;text-align:right;">{int(r['Itens'])}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e8eee9;text-align:right;">{fmt_brl(float(r['Faturamento']))}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e8eee9;text-align:right;">{fmt_pct(float(r['Margem_Media_pct']) if pd.notna(r['Margem_Media_pct']) else None)}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e8eee9;text-align:right;">{fmt_markup(float(r['Markup_Medio']) if pd.notna(r['Markup_Medio']) else None)}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #e8eee9;text-align:right;">{badge}</td>
        </tr>"""

    return intro + _tabela(
        ["Operador", "Pedidos", "Itens", "Faturamento", "Margem média", "Markup médio", "Itens abaixo"],
        linhas,
        ["left", "right", "right", "right", "right", "right", "right"],
    )


def secao_conferencia_resumo(df: pd.DataFrame, periodo: str) -> str:
    n = len(df)
    intro = (
        f"<p style='margin:0 0 16px;'>"
        f"<b>{n}</b> {plural(n, 'cotação', 'cotações')} em andamento (status A) sem envio registrado — <b>{periodo}</b>."
        f"</p>"
    )
    if df.empty:
        return intro + _tabela(
            ["Operador", "Cotação", "Inclusão", "Validade", "Valor"],
            _vazio(5, "Nenhuma pendência de conferência."),
        )

    linhas = ""
    for i, r in df.head(30).iterrows():
        venc = "Vencida" if r.get("Validade_Vencida") else "No prazo"
        cor = "#a33" if r.get("Validade_Vencida") else "#2d5c38"
        linhas += f"""
        <tr style="background:{_zebra(i)};">
          <td style="padding:8px 12px;border-bottom:1px solid #e8eee9;">{r.get('Operador_Nome', '')}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e8eee9;font-weight:600;">{r['Num_Orcamento']}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e8eee9;">{fmt_data(r.get('InsertDate'))}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e8eee9;color:{cor};">{venc}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e8eee9;text-align:right;">{fmt_brl(float(r['Vlr_Orcado']))}</td>
        </tr>"""

    extra = f'<p style="font-size:12px;color:#777;">+ {n - 30} na planilha.</p>' if n > 30 else ""
    return intro + _tabela(
        ["Operador", "Cotação", "Inclusão", "Validade", "Valor"],
        linhas,
        ["left", "left", "left", "left", "right"],
    ) + extra


def montar_email_aviso_rotina_diaria(data_inicio_label: str) -> str:
    nomes = ", ".join(op.nome for op in OPERADORES_PECAS.values())
    corpo = f"""
    <p style="margin:0 0 20px;">Olá, equipe de peças (<b>{nomes}</b>),</p>

    <p style="margin:0 0 16px;">
      A partir de <b>{data_inicio_label}</b>, <b>cada um</b> vai receber <b>todo dia pela manhã</b>
      um e-mail automático só com o <b>seu painel comercial</b> — não é um e-mail da equipe inteira.
    </p>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
      <tr>
        <td style="padding:16px 18px;background:#f4f7f5;border-left:4px solid #3B7A4A;border-radius:0 8px 8px 0;">
          <div style="font-size:15px;font-weight:600;color:#2d5c38;margin-bottom:8px;">Para que serve?</div>
          <div style="font-size:14px;line-height:1.7;color:#444;">
            Ajudar a revisar cotações, preços e pedidos no <b>{NOME_SISTEMA}</b> antes do dia correr.
            É um checklist diário — não é cobrança.
          </div>
        </td>
      </tr>
    </table>

    <p style="margin:0 0 10px;font-size:15px;font-weight:600;color:#2d5c38;">O que vem no e-mail do dia?</p>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
           style="border:1px solid #e0e8e2;border-radius:6px;overflow:hidden;font-size:14px;margin-bottom:24px;">
      <tbody>
        <tr style="background:#fff;">
          <td style="padding:12px 14px;border-bottom:1px solid #e8eee9;width:32px;vertical-align:top;">①</td>
          <td style="padding:12px 14px;border-bottom:1px solid #e8eee9;"><b>Cotações em andamento</b> — conferir se ainda valem e marcar como enviada ou perdida no {NOME_SISTEMA}.</td>
        </tr>
        <tr style="background:#f8faf9;">
          <td style="padding:12px 14px;border-bottom:1px solid #e8eee9;vertical-align:top;">②</td>
          <td style="padding:12px 14px;border-bottom:1px solid #e8eee9;"><b>Cotações com preço baixo</b> — itens abaixo da margem mínima; revisar antes de enviar ao cliente.</td>
        </tr>
        <tr style="background:#fff;">
          <td style="padding:12px 14px;border-bottom:1px solid #e8eee9;vertical-align:top;">③</td>
          <td style="padding:12px 14px;border-bottom:1px solid #e8eee9;"><b>Pedidos novos com preço baixo</b> — prioridade: o pedido já foi lançado no {NOME_SISTEMA}.</td>
        </tr>
        <tr style="background:#f8faf9;">
          <td style="padding:12px 14px;border-bottom:1px solid #e8eee9;vertical-align:top;">④</td>
          <td style="padding:12px 14px;border-bottom:1px solid #e8eee9;"><b>Produtividade da semana</b> — volume de inserções e tempo médio de cotação.</td>
        </tr>
        <tr style="background:#fff;">
          <td style="padding:12px 14px;vertical-align:top;">⑤</td>
          <td style="padding:12px 14px;"><b>Resumo do mês</b> — margem média dos pedidos que <b>você</b> inseriu.</td>
        </tr>
      </tbody>
    </table>

    <p style="margin:0 0 10px;font-size:15px;font-weight:600;color:#2d5c38;">O que fazer quando chegar?</p>
    <ol style="margin:0 0 20px;padding-left:22px;font-size:14px;line-height:1.75;color:#444;">
      <li>Abrir o <b>seu</b> e-mail da manhã (vem com o seu nome no assunto).</li>
      <li>Conferir cada cotação e pedido listados direto no <b>{NOME_SISTEMA}</b>.</li>
      <li>Corrigir preço ou status no sistema — ou avisar o comercial se tiver dúvida.</li>
      <li>No final do e-mail tem o guia <b>“Como ler este e-mail”</b> explicando cada parte.</li>
    </ol>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 20px;">
      <tr>
        <td style="padding:14px 16px;background:#fff3e8;border:1px solid #f0dcc8;border-radius:6px;font-size:14px;line-height:1.65;color:#555;">
          <b>Regra de preço:</b> o valor de venda precisa ser pelo menos <b>40% maior que o custo</b>
          (markup mínimo 1,40). Exemplo: custo R$ 100 → venda mínima R$ 140.
        </td>
      </tr>
    </table>

    <p style="margin:0;font-size:14px;color:#555;">
      Qualquer dúvida sobre o relatório ou o {NOME_SISTEMA}, falem comigo antes da rotina começar.
    </p>
    """
    return montar_email_simples(
        "Nova rotina — e-mail comercial diário",
        f"Início em {data_inicio_label}",
        corpo,
    )


def montar_email_simples(titulo: str, subtitulo: str, corpo_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#eef2ef;font-family:'Segoe UI',Calibri,Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#eef2ef;padding:24px 12px;">
    <tr><td align="center">
      <table role="presentation" width="680" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
        {_secao_titulo(titulo, subtitulo)}
        <tr><td style="padding:28px;color:#333;font-size:15px;line-height:1.55;">
          {corpo_html}
          <p style="margin:24px 0 0;font-size:13px;color:#777;">
            Gerado em {datetime.now().strftime("%d/%m/%Y às %H:%M")}.
          </p>
        </td></tr>
        <tr><td style="background:#f4f7f5;padding:14px 28px;font-size:11px;color:#888;text-align:center;line-height:1.6;">
          Automação comercial interna · Equipe peças<br>
          <span style="color:#aaa;">Desenvolvido por {MARCA_CSA}</span>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


def _filtrar_operador(df: pd.DataFrame, erp: str, col: str = "Operador") -> pd.DataFrame:
    if df.empty or col not in df.columns:
        return df.iloc[0:0].copy()
    return df[df[col].astype(str).str.upper() == erp.upper()].copy()


def _tabela_margem_pessoa(df: pd.DataFrame, doc_col: str, doc_label: str, vazio_msg: str) -> str:
    return _lista_margem_agrupada(df, doc_col, doc_label, vazio_msg)


def _tabela_conferencia_pessoa(df: pd.DataFrame) -> str:
    if df.empty:
        return _tabela(
            ["Cotação", "Inclusão", "Validade", "Valor", "Cliente"],
            _vazio(5, "Nenhuma cotação em andamento para conferir."),
            ["left", "left", "left", "right", "left"],
        )

    linhas = ""
    for i, (_, r) in enumerate(df.iterrows()):
        venc = "Vencida" if r.get("Validade_Vencida") else "No prazo"
        cor = "#a33" if r.get("Validade_Vencida") else "#2d5c38"
        cliente = str(r.get("Cliente", "—"))
        if len(cliente) > 35:
            cliente = cliente[:35] + "…"
        linhas += f"""
        <tr style="background:{_zebra(i)};">
          <td style="padding:8px 12px;border-bottom:1px solid #e8eee9;font-weight:600;">{r['Num_Orcamento']}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e8eee9;">{fmt_data(r.get('InsertDate'))}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e8eee9;color:{cor};">{venc}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e8eee9;text-align:right;">{fmt_brl(float(r['Vlr_Orcado']))}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e8eee9;">{cliente}</td>
        </tr>"""

    return _tabela(
        ["Cotação", "Inclusão", "Validade", "Valor", "Cliente"],
        linhas,
        ["left", "left", "left", "right", "left"],
    )


def _painel_resumo_pessoa(
    op: Operador,
    n_conf: int,
    n_cot: int,
    n_ped: int,
    row_prod: pd.Series | None,
    row_mes: pd.Series | None,
) -> str:
    cot_sem = int(row_prod["Cotacoes"]) if row_prod is not None else 0
    ped_sem = int(row_prod["Pedidos"]) if row_prod is not None else 0
    tempo = row_prod["Tempo_Medio_Fmt"] if row_prod is not None else "—"
    markup_mes = fmt_markup(float(row_mes["Markup_Medio"])) if row_mes is not None and pd.notna(row_mes.get("Markup_Medio")) else "—"
    itens_abaixo = int(row_mes["Itens_Markup_Baixo"]) if row_mes is not None else 0

    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 20px;">
      <tr>
        <td style="padding:10px;background:#f4f7f5;border-radius:6px;text-align:center;width:16%;">
          <div style="font-size:18px;font-weight:700;color:#3B7A4A;">{n_conf}</div>
          <div style="font-size:10px;color:#666;">Conferir</div>
        </td>
        <td style="width:6px;"></td>
        <td style="padding:10px;background:#fff3e8;border-radius:6px;text-align:center;width:16%;">
          <div style="font-size:18px;font-weight:700;color:#c45a11;">{n_cot}</div>
          <div style="font-size:10px;color:#666;">Cot. markup</div>
        </td>
        <td style="width:6px;"></td>
        <td style="padding:10px;background:#fff3e8;border-radius:6px;text-align:center;width:16%;">
          <div style="font-size:18px;font-weight:700;color:#c45a11;">{n_ped}</div>
          <div style="font-size:10px;color:#666;">PV markup</div>
        </td>
        <td style="width:6px;"></td>
        <td style="padding:10px;background:#eef2ef;border-radius:6px;text-align:center;width:16%;">
          <div style="font-size:18px;font-weight:700;">{cot_sem}/{ped_sem}</div>
          <div style="font-size:10px;color:#666;">Cot./ped. semana</div>
        </td>
        <td style="width:6px;"></td>
        <td style="padding:10px;background:#eef2ef;border-radius:6px;text-align:center;width:16%;">
          <div style="font-size:16px;font-weight:700;">{tempo}</div>
          <div style="font-size:10px;color:#666;">Tempo médio</div>
        </td>
        <td style="width:6px;"></td>
        <td style="padding:10px;background:#eef2ef;border-radius:6px;text-align:center;width:16%;">
          <div style="font-size:16px;font-weight:700;">{markup_mes}</div>
          <div style="font-size:10px;color:#666;">Markup mês ({itens_abaixo} abaixo)</div>
        </td>
      </tr>
    </table>"""


def _bloco_pessoa(
    op: Operador,
    periodo_conferencia: str,
    periodo_cotacoes: str,
    periodo_pedidos: str,
    periodo_semana: str,
    periodo_mes: str,
    df_conf: pd.DataFrame,
    df_cot: pd.DataFrame,
    df_ped: pd.DataFrame,
    row_prod: pd.Series | None,
    row_mes: pd.Series | None,
) -> str:
    slug = op.nome.lower().replace(" ", "-")
    n_conf = len(df_conf)
    n_cot = len(df_cot)
    n_ped = len(df_ped)

    sub_conf = (
        f'<h3 style="margin:20px 0 10px;font-size:14px;color:#444;">Cotações em andamento · {periodo_conferencia}</h3>'
        + _tabela_conferencia_pessoa(df_conf)
    )
    n_cot_docs = df_cot["Num_Orcamento"].nunique() if not df_cot.empty else 0
    n_ped_docs = df_ped["PV"].nunique() if not df_ped.empty else 0
    sub_cot = (
        f'<h3 style="margin:20px 0 10px;font-size:14px;color:#444;">'
        f'Cotações com markup &lt; {MARKUP_MINIMO:.2f} · {periodo_cotacoes}'
        f' <span style="color:#888;font-weight:normal;">({n_cot_docs} cot. · {len(df_cot)} itens do dia, custo ≥ R$ 5)</span></h3>'
        + _tabela_margem_pessoa(df_cot, "Num_Orcamento", "Cotação", "Nenhum item de cotação com margem baixa.")
    )
    sub_ped = (
        f'<h3 style="margin:20px 0 10px;font-size:14px;color:#444;">'
        f'Pedidos (PV) com markup &lt; {MARKUP_MINIMO:.2f} · {periodo_pedidos}'
        f' <span style="color:#888;font-weight:normal;">({n_ped_docs} PV · {len(df_ped)} itens do dia, custo ≥ R$ 5)</span></h3>'
        + _tabela_margem_pessoa(df_ped, "PV", "PV", "Nenhum item de pedido com margem baixa.")
    )

    mes_linha = ""
    if row_mes is not None:
        fat = fmt_brl(float(row_mes["Faturamento"]))
        mes_linha = (
            f'<p style="margin:16px 0 0;font-size:13px;color:#555;">'
            f"<b>Mês ({periodo_mes}):</b> {int(row_mes['Pedidos'])} PV · "
            f"{int(row_mes['Itens'])} itens · {fat} faturado · "
            f"margem média {fmt_pct(float(row_mes['Margem_Media_pct']) if pd.notna(row_mes['Margem_Media_pct']) else None)}"
            f"</p>"
        )
    else:
        mes_linha = f'<p style="margin:16px 0 0;font-size:13px;color:#888;">Sem pedidos no mês ({periodo_mes}).</p>'

    return f"""
    <div id="{slug}" style="margin-top:36px;padding-top:28px;border-top:3px solid #3B7A4A;">
      <h2 style="margin:0 0 4px;font-size:19px;color:#2d5c38;">{op.nome}</h2>
      <div style="font-size:13px;color:#888;margin-bottom:16px;">{op.comercial}</div>
      {_painel_resumo_pessoa(op, n_conf, n_cot, n_ped, row_prod, row_mes)}
      {sub_conf}
      {sub_cot}
      {sub_ped}
      {mes_linha}
    </div>"""


def _bloco_guia_comercial(op: Operador | None = None) -> str:
    """Orientação no final do e-mail — linguagem simples para a operadora."""
    if op:
        quem = f", <b>{op.nome}</b>,"
        sujeito = "você"
        verbo_ins = "inseriu"
    else:
        quem = ""
        sujeito = "cada operador(a)"
        verbo_ins = "inseriu"

    return f"""
    <div style="margin-top:40px;padding:20px 22px;background:#f8faf9;border:1px solid #d0ddd4;border-radius:8px;">
      <h2 style="margin:0 0 14px;font-size:17px;color:#2d5c38;">Como ler este e-mail{quem}</h2>
      <p style="margin:0 0 16px;font-size:14px;color:#555;line-height:1.6;">
        Este relatório é automático e ajuda a cuidar de <b>cotações</b>, <b>preços</b> e <b>pedidos</b>
        no dia a dia. Não é cobrança — é um checklist para nada ficar esquecido no {NOME_SISTEMA}.
      </p>

      <div style="font-size:14px;line-height:1.75;color:#333;">
        <p style="margin:0 0 12px;"><b style="color:#2d5c38;">1. Números no topo{" do seu painel" if op else " do bloco"}</b></p>
        <ul style="margin:0 0 18px;padding-left:20px;">
          <li><b>Conferir</b> — cotações que ainda estão <i>em andamento</i> e não aparecem como <i>enviadas</i> no sistema.</li>
          <li><b>Cot. markup</b> — itens em cotação do <b>dia útil anterior</b> com preço abaixo do mínimo.</li>
          <li><b>PV markup</b> — itens em <b>pedidos do dia útil anterior</b> com preço abaixo do mínimo.</li>
          <li><b>Cot./ped. semana</b> — quantas cotações e pedidos {sujeito} {verbo_ins} nos últimos 7 dias.</li>
          <li><b>Tempo médio</b> — tempo entre <i>incluir</i> a cotação e <i>marcar como enviada</i> (referência de agilidade).</li>
          <li><b>Markup mês</b> — média de margem nos pedidos do mês; número entre parênteses = itens ainda abaixo do mínimo.</li>
        </ul>

        <p style="margin:0 0 8px;"><b style="color:#2d5c38;">2. Cotações em andamento</b></p>
        <p style="margin:0 0 16px;padding:12px 14px;background:#fff;border-left:4px solid #3B7A4A;border-radius:0 6px 6px 0;">
          São cotações com status <b>Em andamento (A)</b> que o sistema ainda não registra como enviadas.<br>
          <b>O que fazer:</b><br>
          ① A cotação ainda vale para o cliente? → marcar como <b>enviada</b> no {NOME_SISTEMA}.<br>
          ② Não vale mais? → marcar como <b>perdida</b>.<br>
          ③ Validade vencida? → conferir com o cliente antes de insistir.
        </p>

        <p style="margin:0 0 8px;"><b style="color:#2d5c38;">3. Cotações com margem baixa</b></p>
        <p style="margin:0 0 16px;padding:12px 14px;background:#fff;border-left:4px solid #c45a11;border-radius:0 6px 6px 0;">
          Lista agrupada por número de cotação + cliente. Em cada cotação aparecem os <b>itens</b> com problema de preço.<br>
          <b>O que fazer:</b> revisar o preço <b>antes de enviar</b> a cotação ao cliente. Ajustar no {NOME_SISTEMA} ou alinhar com o comercial se necessário.<br>
          <span style="color:#666;font-size:13px;">Não entram aqui: serviços, itens muito baratos (parafuso, o-ring etc. com custo abaixo de R$ 5).</span>
        </p>

        <p style="margin:0 0 8px;"><b style="color:#2d5c38;">4. Pedidos (PV) com margem baixa</b></p>
        <p style="margin:0 0 16px;padding:12px 14px;background:#fff;border-left:4px solid #c45a11;border-radius:0 6px 6px 0;">
          Mesma regra de preço, mas em <b>pedidos já lançados</b> (PV = número interno do pedido no sistema).<br>
          <b>O que fazer:</b> prioridade alta — o pedido já existe. Conferir preço/custo e corrigir ou avisar o comercial o quanto antes.
        </p>

        <p style="margin:0 0 8px;"><b style="color:#2d5c38;">5. Resumo do mês (última linha do bloco)</b></p>
        <p style="margin:0 0 16px;padding:12px 14px;background:#fff;border-left:4px solid #888;border-radius:0 6px 6px 0;">
          Visão geral dos pedidos que {sujeito} {verbo_ins} no mês: quantidade, valor e margem média.
          Serve para acompanhar a tendência — não é item a item.
        </p>

        <p style="margin:0 0 8px;"><b style="color:#2d5c38;">Regra de preço mínimo (markup {MARKUP_MINIMO:.2f})</b></p>
        <p style="margin:0;padding:12px 14px;background:#eef2ef;border-radius:6px;font-size:13px;line-height:1.65;">
          O preço de venda precisa ser <b>pelo menos 40% maior que o custo</b> da peça.<br>
          Exemplo: custo R$ 100 → venda mínima R$ 140.<br>
          Na tabela, <b>Markup</b> abaixo de <b>{MARKUP_MINIMO:.2f}</b> = preço insuficiente (destacado em vermelho).
          <b>Margem</b> mostra o percentual de lucro sobre a venda.
        </p>
      </div>

      <p style="margin:18px 0 0;font-size:13px;color:#777;">
        Dúvidas? Responda este e-mail ou fale com o comercial responsável.
      </p>
    </div>"""


def _indice_pessoas() -> str:
    links = " · ".join(
        f'<a href="#{op.nome.lower()}" style="color:#3B7A4A;font-weight:600;text-decoration:none;">{op.nome}</a>'
        for op in OPERADORES_PECAS.values()
    )
    return f"""
    <div style="background:#f4f7f5;border:1px solid #e0e8e2;border-radius:6px;padding:14px 16px;margin:20px 0;">
      <div style="font-size:12px;color:#666;margin-bottom:6px;text-transform:uppercase;letter-spacing:.4px;">Conferir por pessoa</div>
      <div style="font-size:15px;">{links}</div>
    </div>"""


def montar_email_rotina_manha(
    periodo_semana: str,
    periodo_mes: str,
    periodo_conferencia: str,
    df_conferencia: pd.DataFrame,
    df_cot_margem: pd.DataFrame,
    df_ped_margem: pd.DataFrame,
    df_prod: pd.DataFrame,
    df_margem_mes: pd.DataFrame,
    periodo_markup: str,
    operador_erp: str | None = None,
    intro_html: str | None = None,
    incluir_guia: bool = True,
    titulo: str | None = None,
    subtitulo: str | None = None,
) -> str:
    periodo_cot_label = periodo_markup
    periodo_ped_label = periodo_markup

    resumo_global = f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:8px;">
      <tr>
        <td style="padding:12px;background:#f4f7f5;border-radius:6px;width:25%;text-align:center;">
          <div style="font-size:22px;font-weight:700;color:#3B7A4A;">{len(df_conferencia)}</div>
          <div style="font-size:11px;color:#666;">Cotações p/ conferir</div>
        </td>
        <td style="width:8px;"></td>
        <td style="padding:12px;background:#fff3e8;border-radius:6px;width:25%;text-align:center;">
          <div style="font-size:22px;font-weight:700;color:#c45a11;">{len(df_cot_margem)}</div>
          <div style="font-size:11px;color:#666;">Itens cotação markup baixo</div>
        </td>
        <td style="width:8px;"></td>
        <td style="padding:12px;background:#fff3e8;border-radius:6px;width:25%;text-align:center;">
          <div style="font-size:22px;font-weight:700;color:#c45a11;">{len(df_ped_margem)}</div>
          <div style="font-size:11px;color:#666;">Itens PV markup baixo</div>
        </td>
        <td style="width:8px;"></td>
        <td style="padding:12px;background:#f4f7f5;border-radius:6px;width:25%;text-align:center;">
          <div style="font-size:22px;font-weight:700;color:#2d5c38;">{int(df_margem_mes['Itens_Markup_Baixo'].sum()) if not df_margem_mes.empty else 0}</div>
          <div style="font-size:11px;color:#666;">Itens mês abaixo mín.</div>
        </td>
      </tr>
    </table>
    <p style="margin:16px 0 0;font-size:14px;color:#555;">
      Regra de margem: preço ≥ custo × <b>{MARKUP_MINIMO:.2f}</b> (mesma lógica do AnaliseCotacao).
    </p>"""

    operadores = OPERADORES_PECAS.values()
    if operador_erp:
        op_filtro = OPERADORES_PECAS.get(operador_erp.upper())
        operadores = [op_filtro] if op_filtro else []

    blocos_pessoa = ""
    for op in operadores:
        row_prod = None
        if not df_prod.empty and "Operador" in df_prod.columns:
            rp = df_prod[df_prod["Operador"] == op.erp]
            if not rp.empty:
                row_prod = rp.iloc[0]
        row_mes = None
        if not df_margem_mes.empty and "Operador" in df_margem_mes.columns:
            rm = df_margem_mes[df_margem_mes["Operador"] == op.erp]
            if not rm.empty:
                row_mes = rm.iloc[0]

        blocos_pessoa += _bloco_pessoa(
            op,
            periodo_conferencia,
            periodo_cot_label,
            periodo_ped_label,
            periodo_semana,
            periodo_mes,
            _filtrar_operador(df_conferencia, op.erp),
            _filtrar_operador(df_cot_margem, op.erp),
            _filtrar_operador(df_ped_margem, op.erp),
            row_prod,
            row_mes,
        )

    op_guia: Operador | None = None
    if operador_erp and operadores:
        op = operadores[0]
        op_guia = op if incluir_guia else None
        intro = intro_html or (
            f'<p style="margin:0 0 12px;">Olá, <b>{op.nome}</b> — segue o resumo da '
            f"sua operação comercial ({op.comercial}).</p>"
        )
        indice = ""
        titulo_final = titulo or f"Rotina comercial — {op.nome}"
        subtitulo_final = subtitulo or f"{op.comercial} · {datetime.now().strftime('%d/%m/%Y')}"
    else:
        intro = intro_html or (
            '<p style="margin:0 0 12px;">Bom dia, <b>Caio</b> — conferência da operação '
            "peças, <b>pessoa por pessoa</b>.</p>"
        )
        indice = _indice_pessoas()
        titulo_final = titulo or "Rotina comercial — manhã"
        subtitulo_final = subtitulo or f"Por operador · {datetime.now().strftime('%d/%m/%Y')}"

    guia = _bloco_guia_comercial(op_guia) if incluir_guia else ""
    corpo = f"{intro}{resumo_global}{indice}{blocos_pessoa}{guia}"

    return montar_email_simples(titulo_final, subtitulo_final, corpo)


def _badge_obs(classificacao: str) -> str:
    if classificacao == "justificada":
        return (
            '<span style="background:#e8f5ec;color:#2d5c38;padding:3px 10px;'
            'border-radius:4px;font-size:12px;font-weight:600;">Justificada</span>'
        )
    if classificacao == "logistica":
        return (
            '<span style="background:#fff3e0;color:#b36b00;padding:3px 10px;'
            'border-radius:4px;font-size:12px;font-weight:600;">Só volume/dimensão</span>'
        )
    return (
        '<span style="background:#fde8e8;color:#a33;padding:3px 10px;'
        'border-radius:4px;font-size:12px;font-weight:600;">Sem justificativa</span>'
    )


def _tabela_itens_conferencia_sexta(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    linhas = ""
    for i, (_, r) in enumerate(df.iterrows()):
        desc = _esc_html(str(r.get("Descricao", "") or "").strip())
        mat = _esc_html(str(r.get("Material", "")))
        item_txt = f"{desc}<br><span style='color:#888;font-size:11px;'>{mat}</span>" if desc else mat
        linhas += f"""
        <tr style="background:{_zebra(i)};">
          <td style="padding:8px 12px;border-bottom:1px solid #e8eee9;">{item_txt}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e8eee9;text-align:right;color:#a33;font-weight:600;">{fmt_markup(float(r['Markup']))}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e8eee9;text-align:right;">{fmt_brl(float(r['Vlr_Unit_Venda']))}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #e8eee9;text-align:right;">{fmt_brl(float(r['Vlr_Custo']))}</td>
        </tr>"""
    return _tabela(
        ["Item", "Markup", "Venda", "Custo"],
        linhas,
        ["left", "right", "right", "right"],
    )


def _docs_agrupados_conferencia_sexta(
    df: pd.DataFrame,
    doc_col: str,
    doc_titulo: str,
) -> tuple[str, int, int]:
    """Retorna HTML, qtd docs sem obs, qtd docs total."""
    if df.empty:
        return "", 0, 0

    partes: list[str] = []
    sem_obs = 0
    total_docs = 0

    for doc_id, grp in df.groupby(doc_col, sort=False):
        total_docs += 1
        obs_txt = grp["Obs_Interna"].iloc[0] if "Obs_Interna" in grp.columns else ""
        if "Obs_Classificacao" in grp.columns:
            classificacao = str(grp["Obs_Classificacao"].iloc[0])
        elif "Obs_Preenchida" in grp.columns:
            classificacao = "justificada" if grp["Obs_Preenchida"].iloc[0] else "vazia"
        else:
            classificacao = "vazia"
        if classificacao != "justificada":
            sem_obs += 1

        cliente = _esc_html(str(grp["Cliente"].iloc[0]) if "Cliente" in grp.columns else "—")
        obs_preview = ""
        if obs_txt and str(obs_txt).strip():
            txt = _esc_html(str(obs_txt).strip())
            if len(txt) > 200:
                txt = txt[:200] + "…"
            cor_obs = "#555" if classificacao == "justificada" else "#888"
            obs_preview = (
                f'<div style="font-size:12px;color:{cor_obs};margin-top:6px;">'
                f"<b>Obs. interna:</b> {txt}</div>"
            )

        borda = {"justificada": "#3B7A4A", "logistica": "#e6a23c"}.get(classificacao, "#c45a11")
        partes.append(f"""
        <div style="margin:14px 0 0;padding:12px 14px;background:#f8faf9;border-left:4px solid {borda};border-radius:0 6px 6px 0;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
            <div>
              <div style="font-size:15px;font-weight:600;color:#2d5c38;">{doc_titulo} {_esc_html(_fmt_doc_id(doc_id))}</div>
              <div style="font-size:13px;color:#555;margin-top:4px;">{cliente}</div>
              {obs_preview}
            </div>
            <div>{_badge_obs(classificacao)}</div>
          </div>
        </div>
        {_tabela_itens_conferencia_sexta(grp)}
        """)

    return "".join(partes), sem_obs, total_docs


def _bloco_operador_conferencia_sexta(
    op: Operador,
    df_cot: pd.DataFrame,
    df_ped: pd.DataFrame,
) -> str:
    html_cot, sem_cot, tot_cot = _docs_agrupados_conferencia_sexta(df_cot, "Num_Orcamento", "Cotação")
    html_ped, sem_ped, tot_ped = _docs_agrupados_conferencia_sexta(df_ped, "PV", "PV")

    if tot_cot == 0 and tot_ped == 0:
        return f"""
        <div style="margin-top:28px;padding-top:20px;border-top:2px solid #e0e8e2;">
          <h2 style="margin:0 0 8px;font-size:17px;color:#2d5c38;">{op.nome} <span style="color:#888;font-weight:normal;">({op.comercial})</span></h2>
          <p style="margin:0;color:#666;font-size:14px;">Nenhum item com markup baixo no período.</p>
        </div>"""

    alerta = ""
    if sem_cot + sem_ped > 0:
        alerta = (
            f'<p style="margin:8px 0 0;color:#a33;font-size:14px;">'
            f"<b>{sem_cot + sem_ped}</b> {plural(sem_cot + sem_ped, 'documento', 'documentos')} "
            f"sem <b>OBSINTERNA</b> no {NOME_SISTEMA}.</p>"
        )

    vazio_cot = '<p style="color:#666">Nenhuma.</p>'
    vazio_ped = '<p style="color:#666">Nenhum.</p>'
    sec_cot = (
        f'<h3 style="margin:20px 0 8px;font-size:14px;color:#444;">Cotações ({tot_cot})</h3>{html_cot or vazio_cot}'
        if tot_cot else ""
    )
    sec_ped = (
        f'<h3 style="margin:20px 0 8px;font-size:14px;color:#444;">Pedidos PV ({tot_ped})</h3>{html_ped or vazio_ped}'
        if tot_ped else ""
    )

    return f"""
    <div style="margin-top:28px;padding-top:20px;border-top:2px solid #e0e8e2;">
      <h2 style="margin:0 0 4px;font-size:17px;color:#2d5c38;">{op.nome} <span style="color:#888;font-weight:normal;">({op.comercial})</span></h2>
      {alerta}
      {sec_cot}
      {sec_ped}
    </div>"""


def montar_email_conferencia_markup_sexta(
    df_cot: pd.DataFrame,
    df_ped: pd.DataFrame,
    periodo_label: str,
) -> str:
    docs_sem_obs = 0
    docs_total = 0
    if not df_cot.empty and "Num_Orcamento" in df_cot.columns:
        for _, g in df_cot.groupby("Num_Orcamento"):
            docs_total += 1
            if not g["Obs_Preenchida"].iloc[0]:
                docs_sem_obs += 1
    if not df_ped.empty and "PV" in df_ped.columns:
        for _, g in df_ped.groupby("PV"):
            docs_total += 1
            if not g["Obs_Preenchida"].iloc[0]:
                docs_sem_obs += 1

    blocos = ""
    for op in OPERADORES_PECAS.values():
        cot_o = df_cot[df_cot["Operador"] == op.erp] if not df_cot.empty else df_cot
        ped_o = df_ped[df_ped["Operador"] == op.erp] if not df_ped.empty else df_ped
        blocos += _bloco_operador_conferencia_sexta(op, cot_o, ped_o)

    corpo = f"""
    <p style="margin:0 0 16px;">Bom dia, <b>Caio</b> — conferência semanal de markup baixo e justificativas no <b>{NOME_SISTEMA}</b>.</p>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:20px;">
      <tr>
        <td style="padding:14px;background:#f4f7f5;border-radius:6px;text-align:center;width:33%;">
          <div style="font-size:22px;font-weight:700;">{docs_total}</div>
          <div style="font-size:11px;color:#666;">Documentos com markup baixo</div>
        </td>
        <td style="width:8px;"></td>
        <td style="padding:14px;background:#fff3e8;border-radius:6px;text-align:center;width:33%;">
          <div style="font-size:22px;font-weight:700;color:#c45a11;">{docs_sem_obs}</div>
          <div style="font-size:11px;color:#666;">Sem OBSINTERNA</div>
        </td>
        <td style="width:8px;"></td>
        <td style="padding:14px;background:#e8f5ec;border-radius:6px;text-align:center;width:33%;">
          <div style="font-size:22px;font-weight:700;color:#2d5c38;">{docs_total - docs_sem_obs}</div>
          <div style="font-size:11px;color:#666;">Justificados</div>
        </td>
      </tr>
    </table>

    <p style="margin:0 0 20px;font-size:14px;color:#555;line-height:1.6;">
      Período: <b>{periodo_label}</b><br>
      Inclui a <b>sexta da semana passada</b> + <b>segunda a quinta</b> desta semana
      (o que foi enviado nos e-mails diários).<br>
      Verificar campo <b>OBSINTERNA</b> no cabeçalho da cotação ou do pedido no {NOME_SISTEMA}
      (motivo do markup baixo: desconto, reajuste de custo, autorização etc.).<br>
      <b>Não conta</b> como justificativa: volume, peso, palete ou dimensões (ex.: 80KG 90X40X45).
      Quem não justificou pode ser cobrado novamente.
    </p>

    {blocos}
    """
    return montar_email_simples(
        "Conferência semanal — markup e justificativas",
        periodo_label,
        corpo,
    )
