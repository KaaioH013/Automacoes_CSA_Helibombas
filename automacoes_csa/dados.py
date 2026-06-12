"""Consultas ERP para automações comerciais."""

from __future__ import annotations

import pandas as pd

from automacoes_csa.comum import (
    CUSTO_MINIMO_ITEM,
    FILTROS_PEDIDO_PECAS,
    MATERIAL_SERVICO,
    MARKUP_MINIMO,
    MAX_MINUTOS_SESSAO,
    OPERADORES_ERP_SQL,
    OPERADORES_PECAS,
    Operador,
    fmt_minutos,
    classificar_obs_interna,
    obs_interna_preenchida,
)
from automacoes_csa.markup_custo import (
    CUSTO_UNITARIO_ORCAMENTO,
    CUSTO_UNITARIO_PEDIDO,
    JOIN_CUSTO_ORCAMENTO,
    JOIN_CUSTO_PEDIDO,
)


def buscar_itens_cotacao_margem_baixa(
    engine, dt_ini: str, dt_fim_exclusivo: str, markup_min: float = MARKUP_MINIMO
) -> pd.DataFrame:
    custo = CUSTO_UNITARIO_ORCAMENTO
    sql = f"""
    SELECT
        o.NUMERO                          AS Num_Orcamento,
        UPPER(LTRIM(RTRIM(o.INSERTNAME))) AS Operador,
        o.DTCADASTRO                      AS Dt_Cadastro,
        o.STATUS                          AS Status_Orc,
        f.RAZAO                           AS Cliente,
        oi.SEQ                            AS Seq,
        oi.MATERIAL                       AS Material,
        oi.DESCRICAO                      AS Descricao,
        oi.QTDE                           AS Qtde,
        oi.VLRUNITARIO                    AS Vlr_Unit_Venda,
        ({custo})                         AS Vlr_Custo,
        ROUND(oi.VLRUNITARIO / NULLIF(({custo}), 0), 2) AS Markup,
        ROUND(
            (oi.VLRUNITARIO - ({custo})) / NULLIF(oi.VLRUNITARIO, 0) * 100, 1
        )                                 AS Margem_pct,
        oi.VLRTOTAL                       AS Vlr_Total,
        CAST(o.OBSINTERNA AS VARCHAR(MAX)) AS Obs_Interna
    FROM VE_ORCAMENTOITENS oi
    JOIN VE_ORCAMENTOS o ON o.CODIGO = oi.ORCAMENTO
    LEFT JOIN FN_FORNECEDORES f ON f.CODIGO = o.CODCLIENTE
    {JOIN_CUSTO_ORCAMENTO}
    WHERE o.DTCADASTRO >= '{dt_ini}'
      AND o.DTCADASTRO <  '{dt_fim_exclusivo}'
      AND o.FILIAL IN (1, 2)
      AND oi.MATERIAL NOT LIKE '8%'
      AND oi.MATERIAL <> '{MATERIAL_SERVICO}'
      AND oi.VLRUNITARIO > 0
      AND ({custo}) >= {CUSTO_MINIMO_ITEM}
      AND oi.VLRUNITARIO / ({custo}) < {markup_min}
      AND UPPER(LTRIM(RTRIM(ISNULL(o.INSERTNAME, '')))) IN ({OPERADORES_ERP_SQL})
    ORDER BY o.INSERTDATE DESC, o.NUMERO, oi.SEQ
    """
    return _enriquecer_itens_margem(pd.read_sql(sql, engine))


def _nome_operador(u: str) -> str:
    return OPERADORES_PECAS.get(u, Operador(u, u, "", "")).nome


def buscar_itens_pedido_margem_baixa(
    engine, dt_ini: str, dt_fim_exclusivo: str, markup_min: float = MARKUP_MINIMO
) -> pd.DataFrame:
    custo = CUSTO_UNITARIO_PEDIDO
    sql = f"""
    SELECT
        p.CODIGO                          AS PV,
        p.NUMINTERNO                      AS Nr_Interno,
        p.DTPEDIDO                        AS Dt_Pedido,
        UPPER(LTRIM(RTRIM(p.USERNAME1)))  AS Operador,
        f.RAZAO                           AS Cliente,
        i.SEQ                             AS Seq,
        i.MATERIAL                        AS Material,
        i.DESCRICAO                       AS Descricao,
        i.QTDE                            AS Qtde,
        i.VLRUNITARIO                     AS Vlr_Unit_Venda,
        ({custo})                         AS Vlr_Custo,
        ROUND(i.VLRUNITARIO / NULLIF(({custo}), 0), 2) AS Markup,
        ROUND(
            (i.VLRUNITARIO - ({custo})) / NULLIF(i.VLRUNITARIO, 0) * 100, 1
        )                                 AS Margem_pct,
        i.VLRTOTAL                        AS Vlr_Total,
        CAST(p.OBSINTERNA AS VARCHAR(MAX)) AS Obs_Interna
    FROM VE_PEDIDOITENS i
    JOIN VE_PEDIDO p ON p.CODIGO = i.PEDIDO
    LEFT JOIN FN_FORNECEDORES f ON f.CODIGO = p.CLIENTE
    {JOIN_CUSTO_PEDIDO}
    WHERE p.DTPEDIDO >= '{dt_ini}'
      AND p.DTPEDIDO <  '{dt_fim_exclusivo}'
      {FILTROS_PEDIDO_PECAS}
      AND ({custo}) >= {CUSTO_MINIMO_ITEM}
      AND i.VLRUNITARIO > 0
      AND i.VLRUNITARIO / ({custo}) < {markup_min}
      AND UPPER(LTRIM(RTRIM(ISNULL(p.USERNAME1, '')))) IN ({OPERADORES_ERP_SQL})
    ORDER BY p.DTPEDIDO DESC, p.CODIGO, i.SEQ
    """
    return _enriquecer_itens_margem(pd.read_sql(sql, engine))


def _enriquecer_itens_margem(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df[df["Vlr_Custo"].fillna(0) >= CUSTO_MINIMO_ITEM].copy()
    df = df[df["Material"].astype(str) != MATERIAL_SERVICO].copy()
    df["Operador_Nome"] = df["Operador"].map(_nome_operador)
    if "Obs_Interna" in df.columns:
        df["Obs_Classificacao"] = df["Obs_Interna"].map(classificar_obs_interna)
        df["Obs_Preenchida"] = df["Obs_Classificacao"].eq("justificada")
    return df


def buscar_cotacoes_andamento(
    engine, dt_ini: str | None = None, dt_fim_exclusivo: str | None = None
) -> pd.DataFrame:
    filtro_data = ""
    if dt_ini and dt_fim_exclusivo:
        filtro_data = f"""
      AND o.DTCADASTRO >= '{dt_ini}'
      AND o.DTCADASTRO <  '{dt_fim_exclusivo}'"""
    sql = f"""
    SELECT
        o.NUMERO AS Num_Orcamento,
        UPPER(LTRIM(RTRIM(o.INSERTNAME))) AS Operador,
        o.INSERTDATE,
        o.DTVALIDADE,
        o.DTCADASTRO,
        ISNULL(o.VLRORCADO, 0) AS Vlr_Orcado,
        f.RAZAO AS Cliente
    FROM VE_ORCAMENTOS o
    LEFT JOIN FN_FORNECEDORES f ON f.CODIGO = o.CODCLIENTE
    WHERE o.FILIAL IN (1, 2)
      {filtro_data}
      AND o.STATUS = 'A'
      AND UPPER(LTRIM(RTRIM(ISNULL(o.INSERTNAME, '')))) IN ({OPERADORES_ERP_SQL})
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
    if not df.empty:
        df["InsertDate"] = pd.to_datetime(df["INSERTDATE"], errors="coerce")
        df["DtValidade"] = pd.to_datetime(df["DTVALIDADE"], errors="coerce")
        hoje = pd.Timestamp.now().normalize()
        df["Validade_Vencida"] = df["DtValidade"].notna() & (df["DtValidade"] < hoje)
        df["Operador_Nome"] = df["Operador"].map(_nome_operador)
    return df


def buscar_produtividade_semanal(engine, dt_ini: str, dt_fim_exclusivo: str) -> pd.DataFrame:
    """Inserções + tempo médio cotação→envio (sessão 8h) por operador peças."""
    sql_cot_det = f"""
    SELECT
        UPPER(LTRIM(RTRIM(ISNULL(o.INSERTNAME, '')))) AS Operador,
        o.INSERTDATE,
        o.DTENVIO
    FROM VE_ORCAMENTOS o
    WHERE o.DTCADASTRO >= '{dt_ini}'
      AND o.DTCADASTRO <  '{dt_fim_exclusivo}'
      AND o.FILIAL IN (1, 2)
      AND UPPER(LTRIM(RTRIM(ISNULL(o.INSERTNAME, '')))) IN ({OPERADORES_ERP_SQL})
    """
    sql_ped = f"""
    SELECT
        UPPER(LTRIM(RTRIM(ISNULL(p.USERNAME1, '')))) AS Operador,
        COUNT(*) AS Pedidos
    FROM VE_PEDIDO p
    WHERE p.DTPEDIDO >= '{dt_ini}'
      AND p.DTPEDIDO <  '{dt_fim_exclusivo}'
      AND p.STATUS <> 'C'
      AND p.FILIAL IN (1, 2)
      AND UPPER(LTRIM(RTRIM(ISNULL(p.USERNAME1, '')))) IN ({OPERADORES_ERP_SQL})
    GROUP BY UPPER(LTRIM(RTRIM(ISNULL(p.USERNAME1, ''))))
    """
    cot = pd.read_sql(sql_cot_det, engine)
    ped = pd.read_sql(sql_ped, engine)

    linhas = []
    for erp, op in OPERADORES_PECAS.items():
        g = cot[cot["Operador"] == erp]
        insert_dt = pd.to_datetime(g["INSERTDATE"], errors="coerce")
        envio_dt = pd.to_datetime(g["DTENVIO"], errors="coerce")
        tem_hora = (
            envio_dt.notna()
            & ((envio_dt.dt.hour != 0) | (envio_dt.dt.minute != 0) | (envio_dt.dt.second != 0))
        )
        minutos = (envio_dt - insert_dt).dt.total_seconds() / 60.0
        minutos = minutos.where(tem_hora & (minutos >= 0))
        sessao = minutos.where(minutos <= MAX_MINUTOS_SESSAO)

        ped_row = ped[ped["Operador"] == erp]
        qtd_ped = int(ped_row["Pedidos"].iloc[0]) if not ped_row.empty else 0

        media_sess = sessao.dropna()
        linhas.append({
            "Operador": erp,
            "Nome": op.nome,
            "Comercial": op.comercial,
            "Cotacoes": len(g),
            "Pedidos": qtd_ped,
            "Com_Envio": int(tem_hora.sum()),
            "Tempo_Medio_Min": round(media_sess.mean(), 1) if not media_sess.empty else None,
            "Tempo_Medio_Fmt": fmt_minutos(media_sess.mean()) if not media_sess.empty else "—",
        })

    return pd.DataFrame(linhas)


def buscar_margem_mes_por_operador(engine, dt_ini: str, dt_fim_exclusivo: str) -> pd.DataFrame:
    custo = CUSTO_UNITARIO_PEDIDO
    sql = f"""
    SELECT
        UPPER(LTRIM(RTRIM(ISNULL(p.USERNAME1, '')))) AS Operador,
        COUNT(DISTINCT p.CODIGO) AS Pedidos,
        COUNT(i.CODIGO) AS Itens,
        SUM(i.VLRTOTAL) AS Faturamento,
        SUM(CASE WHEN ({custo}) > 0 THEN 1 ELSE 0 END) AS Itens_Com_Custo,
        ROUND(AVG(
            CASE WHEN ({custo}) > 0 AND i.VLRUNITARIO > 0
                 THEN (i.VLRUNITARIO - ({custo})) / i.VLRUNITARIO * 100
                 ELSE NULL END
        ), 1) AS Margem_Media_pct,
        ROUND(AVG(
            CASE WHEN ({custo}) > 0 AND i.VLRUNITARIO > 0
                 THEN i.VLRUNITARIO / ({custo})
                 ELSE NULL END
        ), 2) AS Markup_Medio,
        SUM(CASE
            WHEN ({custo}) >= {CUSTO_MINIMO_ITEM} AND i.VLRUNITARIO > 0
                 AND i.VLRUNITARIO / ({custo}) < {MARKUP_MINIMO}
            THEN 1 ELSE 0 END) AS Itens_Markup_Baixo,
        SUM(CASE WHEN ({custo}) > 0
                 THEN (i.VLRUNITARIO - ({custo})) * i.QTDE
                 ELSE 0 END) AS Lucro_Bruto_Est
    FROM VE_PEDIDOITENS i
    JOIN VE_PEDIDO p ON p.CODIGO = i.PEDIDO
    {JOIN_CUSTO_PEDIDO}
    WHERE p.DTPEDIDO >= '{dt_ini}'
      AND p.DTPEDIDO <  '{dt_fim_exclusivo}'
      {FILTROS_PEDIDO_PECAS}
      AND UPPER(LTRIM(RTRIM(ISNULL(p.USERNAME1, '')))) IN ({OPERADORES_ERP_SQL})
    GROUP BY UPPER(LTRIM(RTRIM(ISNULL(p.USERNAME1, ''))))
    ORDER BY Faturamento DESC
    """
    df = pd.read_sql(sql, engine)
    if not df.empty:
        df["Nome"] = df["Operador"].map(_nome_operador)
        df["Comercial"] = df["Operador"].map(
            lambda u: OPERADORES_PECAS.get(u, Operador(u, u, "", "")).comercial
        )
    return df
