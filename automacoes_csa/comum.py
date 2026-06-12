"""Constantes e utilitários compartilhados — automações comerciais peças."""

from __future__ import annotations

import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

MARCA_CSA = "CSA®"
DESTINATARIO_PADRAO = "comercial1@helibombas.com.br"
EMAILS_EQUIPE_PECAS = (
    "comercial1@helibombas.com.br",
    "comercial6@helibombas.com.br",
    "comercial4@helibombas.com.br",
)
NOME_SISTEMA = "Sectra"
MARKUP_MINIMO = 1.40  # custo x 1,40 = markup mínimo aceitável (40% sobre custo)
CUSTO_MINIMO_ITEM = 5.00  # ignora parafuso, o-ring etc. (custo unitário abaixo disso)
MATERIAL_SERVICO = "140100101"  # serviço (montagem etc.) — fora da análise de margem de peças

TPVENDA_EXCLUIR = (7, 21, 5, 12, 24, 11, 26, 6, 15, 16, 8, 19, 9, 17, 53, 18, 65, 23)
TPVENDA_STR = ",".join(str(x) for x in TPVENDA_EXCLUIR)

FILTROS_PEDIDO_PECAS = f"""
    AND p.STATUS <> 'C'
    AND i.STATUS <> 'C'
    AND i.TPVENDA NOT IN ({TPVENDA_STR})
    AND i.MATERIAL NOT LIKE '8%'
    AND i.MATERIAL <> '{MATERIAL_SERVICO}'
    AND i.FLAGSUB <> 'S'
    AND p.CODIGO NOT IN (
        SELECT p2.CODIGO FROM VE_PEDIDO p2
        JOIN FN_FORNECEDORES f2 ON f2.CODIGO = p2.CLIENTE
        WHERE f2.UF = 'EX'
    )
"""

MAX_MINUTOS_SESSAO = 480


@dataclass(frozen=True)
class Operador:
    erp: str
    nome: str
    comercial: str
    email: str


OPERADORES_PECAS: dict[str, Operador] = {
    "CAIOSANTANA": Operador(
        "CAIOSANTANA", "Caio", "Comercial 1", "comercial1@helibombas.com.br"
    ),
    "PRISCILASANTORO": Operador(
        "PRISCILASANTORO", "Priscila", "Comercial 6", "comercial6@helibombas.com.br"
    ),
    "PATRICIA": Operador(
        "PATRICIA", "Patricia", "Comercial 4", "comercial4@helibombas.com.br"
    ),
}

OPERADORES_ERP_SQL = ", ".join(f"'{k}'" for k in OPERADORES_PECAS)


def destinatarios(para: str | None = None) -> list[str]:
    raw = para or os.getenv("ALERTAS_EMAIL_TO") or DESTINATARIO_PADRAO
    return [e.strip() for e in raw.split(",") if e.strip()]


def destinatarios_equipe_pecas(para: str | None = None) -> list[str]:
    """Caio, Priscila e Patricia — override via COMERCIAL_PECAS_EMAILS ou --para."""
    if para:
        return destinatarios(para)
    raw = os.getenv("COMERCIAL_PECAS_EMAILS")
    if raw:
        return [e.strip() for e in raw.split(",") if e.strip()]
    return [op.email for op in OPERADORES_PECAS.values()]


def email_operador(erp: str) -> str:
    """E-mail do operador (respeita COMERCIAL_PECAS_EMAILS na mesma ordem)."""
    equipe = destinatarios_equipe_pecas()
    keys = list(OPERADORES_PECAS.keys())
    if erp in keys:
        idx = keys.index(erp)
        if idx < len(equipe):
            return equipe[idx]
    return OPERADORES_PECAS[erp].email


def proxima_segunda_rotina() -> tuple[date, str]:
    """Data da próxima segunda-feira (hoje se já for segunda)."""
    hoje = date.today()
    if hoje.weekday() == 0:
        d = hoje
    else:
        d = hoje + timedelta(days=7 - hoje.weekday())
    meses = (
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
    )
    label = f"segunda-feira, {d.day} de {meses[d.month - 1]} de {d.year}"
    return d, label


def cc_list(cc: str | None = None) -> list[str] | None:
    raw = cc or os.getenv("ALERTAS_EMAIL_CC") or ""
    lst = [e.strip() for e in raw.split(",") if e.strip()]
    return lst or None


def plural(n: int, singular: str, plural_form: str) -> str:
    return singular if n == 1 else plural_form


def fmt_brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_data(v) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return "—"
    return pd_to_datetime(v).strftime("%d/%m/%Y")


def pd_to_datetime(v):
    import pandas as pd

    return pd.to_datetime(v, errors="coerce")


def fmt_pct(v: float | None) -> str:
    if v is None or v != v:
        return "—"
    return f"{v:.1f}%"


def fmt_markup(v: float | None) -> str:
    if v is None or v != v:
        return "—"
    return f"{v:.2f}"


def fmt_minutos(minutos: float | None) -> str:
    if minutos is None or minutos != minutos:
        return "—"
    m = int(round(minutos))
    h, r = divmod(m, 60)
    if h:
        return f"{h}h{r:02d}m"
    return f"{m} min"


def periodo_semana_ate_hoje() -> tuple[str, str, str]:
    """Últimos 7 dias corridos (inclusive hoje). Retorna (dt_ini, dt_fim_exclusivo, label)."""
    hoje = date.today()
    ini = hoje - timedelta(days=6)
    fim_excl = hoje + timedelta(days=1)
    label = f"{ini.strftime('%d/%m')} a {hoje.strftime('%d/%m/%Y')}"
    return ini.isoformat(), fim_excl.isoformat(), label


def periodo_dias(dias: int) -> tuple[str, str, str]:
    hoje = date.today()
    ini = hoje - timedelta(days=dias - 1)
    fim_excl = hoje + timedelta(days=1)
    label = f"últimos {dias} dias ({ini.strftime('%d/%m')} a {hoje.strftime('%d/%m/%Y')})"
    return ini.isoformat(), fim_excl.isoformat(), label


def periodo_conferencia_pendentes() -> tuple[str | None, str | None, str]:
    """Cotações em andamento: sem corte de data — ficam até a pessoa arrumar."""
    return None, None, "pendentes (até regularizar no Sectra)"


def periodo_markup_semana_sexta(hoje: date | None = None) -> tuple[str, str, str]:
    """Sexta de manhã: sex. anterior + seg a qui da semana atual (5 dias úteis)."""
    ref = hoje or date.today()
    if ref.weekday() != 4:
        # Ajusta para a sexta da semana de referência (teste fora de sexta)
        ref = ref - timedelta(days=(ref.weekday() - 4) % 7)
    sexta_anterior = ref - timedelta(days=7)
    segunda_atual = ref - timedelta(days=4)
    quinta_atual = ref - timedelta(days=1)
    dt_ini = sexta_anterior.isoformat()
    dt_fim_excl = ref.isoformat()
    label = (
        f"sexta {sexta_anterior.strftime('%d/%m')} + "
        f"seg {segunda_atual.strftime('%d/%m')} a qui {quinta_atual.strftime('%d/%m/%Y')}"
    )
    return dt_ini, dt_fim_excl, label


def _norm_obs_interna(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", t.lower()).strip()


# Palavras que indicam motivo comercial de markup baixo
_OBS_JUSTIF_KW = (
    "desconto", "autoriz", "aprov", "liberad", "negociad", "combinad",
    "reajust", "markup", "margem", "custo", "preco", "valor",
    "motivo", "justific", "excecao", "especial",
    "cotacao", "envio", "concorr", "promoc",
    "acord", "bonific", "brinde", "amostra", "garantia",
    "erro de", "digita", "cadastr", "perd", "fechad",
)

# Volume, peso, dimensão — não conta como justificativa de margem
_OBS_LOG_KW = (
    "volume", "volumes", "vol.", " vol ",
    "palete", "palette", "pallet", "pallets",
    "caixa", "embalag", "dimens",
)

_RE_OBS_DIMS = re.compile(r"\d+\s*[xX]\s*\d+\s*[xX]\s*\d+")
_RE_OBS_KG = re.compile(r"\b\d+\s*kg\b", re.I)
_RE_OBS_RS_DE_PARA = re.compile(
    r"r\$\s*[\d.,]+\s*(?:para|p/)\s*r\$\s*[\d.,]+", re.I
)
_RE_OBS_MATERIAL = re.compile(r"material\s+\d{5,}", re.I)
_RE_OBS_AUTORIZADO_POR = re.compile(
    r"(?:autoriz|aprov|liberad)[oa]?\s+por\s+\w", re.I
)


def classificar_obs_interna(valor) -> str:
    """Classifica OBSINTERNA: vazia | logistica | justificada."""
    if valor is None or (isinstance(valor, float) and valor != valor):
        return "vazia"
    bruto = str(valor).strip()
    if not bruto:
        return "vazia"

    t = _norm_obs_interna(bruto)

    if (
        _RE_OBS_RS_DE_PARA.search(t)
        or _RE_OBS_MATERIAL.search(t)
        or _RE_OBS_AUTORIZADO_POR.search(t)
        or any(kw in t for kw in _OBS_JUSTIF_KW)
        or re.search(r"r\$\s*\d", t)
    ):
        return "justificada"

    log_hits = sum(1 for kw in _OBS_LOG_KW if kw in t)
    has_dims = bool(_RE_OBS_DIMS.search(bruto))
    has_kg = bool(_RE_OBS_KG.search(t))
    has_vol_num = bool(re.search(r"\b\d+\s+volume|\bvolume\s+\d+", t))

    resto = t
    resto = _RE_OBS_DIMS.sub(" ", resto)
    resto = _RE_OBS_KG.sub(" ", resto)
    resto = re.sub(r"\b\d+\b", " ", resto)
    for kw in _OBS_LOG_KW:
        resto = resto.replace(kw, " ")
    resto = re.sub(r"\s+", " ", resto).strip()

    logistica_forte = has_dims or has_kg or has_vol_num or log_hits >= 1

    if logistica_forte and len(resto) <= 3:
        return "logistica"

    if (has_dims and has_kg) or (has_dims and log_hits >= 1) or (has_kg and log_hits >= 1):
        if len(resto) < 20:
            return "logistica"

    if log_hits >= 1 and len(t) < 60:
        palavras = [
            w for w in re.findall(r"[a-z]{4,}", t)
            if w not in ("volume", "volumes", "palete", "palette", "pallet", "caixa")
        ]
        if not palavras:
            return "logistica"

    if len(t) >= 30 and not logistica_forte:
        return "justificada"

    if logistica_forte:
        return "logistica"

    return "vazia"


def obs_interna_preenchida(valor) -> bool:
    """True só quando a obs parece justificar markup baixo (não volume/dimensão)."""
    return classificar_obs_interna(valor) == "justificada"


def periodo_markup_dia_util_anterior() -> tuple[str, str, str]:
    """Markup diário: revisa só o dia útil anterior (seg→sex, ter→seg, …)."""
    hoje = date.today()
    if hoje.weekday() == 0:
        alvo = hoje - timedelta(days=3)
    else:
        alvo = hoje - timedelta(days=1)
    nomes = (
        "segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
        "sexta-feira", "sábado", "domingo",
    )
    label = f"{nomes[alvo.weekday()]}, {alvo.strftime('%d/%m/%Y')}"
    dt_ini = alvo.isoformat()
    dt_fim = (alvo + timedelta(days=1)).isoformat()
    return dt_ini, dt_fim, label


def periodo_mes_atual() -> tuple[str, str, str]:
    hoje = date.today()
    ini = date(hoje.year, hoje.month, 1)
    if hoje.month == 12:
        fim_excl = date(hoje.year + 1, 1, 1)
    else:
        fim_excl = date(hoje.year, hoje.month + 1, 1)
    meses = (
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
    )
    label = f"{meses[hoje.month - 1]} de {hoje.year}"
    return ini.isoformat(), fim_excl.isoformat(), label


def sql_escape(s: str) -> str:
    return s.replace("'", "''")
