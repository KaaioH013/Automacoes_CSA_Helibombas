"""
email_sender.py — Envio de e-mail reutilizável por todos os scripts.

Dois backends suportados:

1. OUTLOOK (recomendado em ambiente corporativo com Outlook Classic instalado)
   - Usa COM (win32com.client) e a sessão autenticada do Outlook do usuário.
   - Sem senha, sem MFA, sem SMTP AUTH. Envia como o usuário logado e
     o e-mail aparece em "Itens Enviados" do Outlook normalmente.
   - Configuração: EMAIL_BACKEND=outlook

2. SMTP (Office 365, Gmail, qualquer servidor SMTP padrão)
   - Configuração: EMAIL_BACKEND=smtp (ou ausente — default)

Configuração via .env:
    EMAIL_BACKEND   outlook | smtp           (default: smtp)

    # quando EMAIL_BACKEND=smtp
    SMTP_HOST       (ex.: smtp.office365.com)
    SMTP_PORT       (default 587)
    SMTP_USER       (login SMTP — geralmente o próprio e-mail remetente)
    SMTP_PASSWORD   (senha ou app password)
    SMTP_FROM       (e-mail remetente; opcional — usa SMTP_USER se vazio)
    SMTP_FROM_NAME  (nome amigável do remetente; opcional)
    SMTP_USE_TLS    (default true — STARTTLS na porta 587)
    SMTP_USE_SSL    (default false — SMTP_SSL na porta 465; ignora TLS se true)

    # quando EMAIL_BACKEND=outlook
    OUTLOOK_CONTA   (opcional — nome/e-mail da conta a usar se houver várias)
    OUTLOOK_SALVAR_RASCUNHO  (default false — se true, salva como rascunho ao invés de enviar)

Uso:
    from email_sender import enviar_email
    enviar_email(
        destinatarios=["fulano@helibombas.com.br"],
        assunto="Assunto",
        corpo_html="<p>Olá</p>",
        anexos=[Path("exports/arquivo.xlsx")],
    )
"""

from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv

load_dotenv()


class EmailConfigError(RuntimeError):
    pass


def _bool_env(nome: str, default: bool) -> bool:
    v = os.getenv(nome)
    if v is None or v.strip() == "":
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "sim", "on")


def _ler_config() -> dict:
    host = (os.getenv("SMTP_HOST") or "").strip()
    user = (os.getenv("SMTP_USER") or "").strip()
    password = os.getenv("SMTP_PASSWORD") or ""
    if not host or not user or not password:
        faltando = []
        if not host:
            faltando.append("SMTP_HOST")
        if not user:
            faltando.append("SMTP_USER")
        if not password:
            faltando.append("SMTP_PASSWORD")
        raise EmailConfigError(
            "Configuração SMTP incompleta no .env (faltam: " + ", ".join(faltando) + ")"
        )

    return {
        "host": host,
        "port": int(os.getenv("SMTP_PORT") or "587"),
        "user": user,
        "password": password,
        "from_addr": (os.getenv("SMTP_FROM") or user).strip(),
        "from_name": (os.getenv("SMTP_FROM_NAME") or "").strip(),
        "use_tls": _bool_env("SMTP_USE_TLS", True),
        "use_ssl": _bool_env("SMTP_USE_SSL", False),
    }


def enviar_email(
    destinatarios: Iterable[str],
    assunto: str,
    corpo_html: str,
    corpo_texto: str | None = None,
    anexos: Iterable[Path] | None = None,
    cc: Iterable[str] | None = None,
    bcc: Iterable[str] | None = None,
) -> None:
    """Envia um e-mail. Lança EmailConfigError se a configuração estiver incompleta.

    Escolhe automaticamente o backend (Outlook COM ou SMTP) conforme
    a variável EMAIL_BACKEND no .env (default: smtp).
    """
    backend = (os.getenv("EMAIL_BACKEND") or "smtp").strip().lower()
    if backend == "outlook":
        return _enviar_via_outlook(
            destinatarios=destinatarios,
            assunto=assunto,
            corpo_html=corpo_html,
            anexos=anexos,
            cc=cc,
            bcc=bcc,
        )
    return _enviar_via_smtp(
        destinatarios=destinatarios,
        assunto=assunto,
        corpo_html=corpo_html,
        corpo_texto=corpo_texto,
        anexos=anexos,
        cc=cc,
        bcc=bcc,
    )


def _enviar_via_outlook(
    destinatarios: Iterable[str],
    assunto: str,
    corpo_html: str,
    anexos: Iterable[Path] | None = None,
    cc: Iterable[str] | None = None,
    bcc: Iterable[str] | None = None,
) -> None:
    try:
        import win32com.client  # type: ignore
        import pythoncom  # type: ignore
    except ImportError as e:
        raise EmailConfigError(
            "Backend 'outlook' requer pywin32. Instale com: pip install pywin32"
        ) from e

    destinatarios_list = [d.strip() for d in destinatarios if d and d.strip()]
    cc_list = [c.strip() for c in (cc or []) if c and c.strip()]
    bcc_list = [b.strip() for b in (bcc or []) if b and b.strip()]
    if not destinatarios_list:
        raise EmailConfigError("Lista de destinatários vazia")

    OL_MAIL_ITEM = 0
    OL_FORMAT_HTML = 2

    pythoncom.CoInitialize()
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(OL_MAIL_ITEM)

        conta_alvo = (os.getenv("OUTLOOK_CONTA") or "").strip()
        if conta_alvo:
            try:
                accounts = outlook.Session.Accounts
                escolhida = None
                for i in range(1, accounts.Count + 1):
                    acc = accounts.Item(i)
                    nome = (acc.DisplayName or "").lower()
                    smtp = (acc.SmtpAddress or "").lower()
                    if conta_alvo.lower() in nome or conta_alvo.lower() == smtp:
                        escolhida = acc
                        break
                if escolhida is not None:
                    mail._oleobj_.Invoke(*(64209, 0, 8, 0, escolhida))  # SendUsingAccount
            except Exception:
                pass

        mail.To = "; ".join(destinatarios_list)
        if cc_list:
            mail.CC = "; ".join(cc_list)
        if bcc_list:
            mail.BCC = "; ".join(bcc_list)
        mail.Subject = assunto
        mail.BodyFormat = OL_FORMAT_HTML
        mail.HTMLBody = corpo_html

        for anexo in anexos or []:
            caminho = Path(anexo).resolve()
            if caminho.exists():
                mail.Attachments.Add(str(caminho))

        salvar_rascunho = (os.getenv("OUTLOOK_SALVAR_RASCUNHO") or "").strip().lower() in (
            "1", "true", "yes", "y", "sim", "on",
        )
        if salvar_rascunho:
            mail.Save()
        else:
            mail.Send()
    finally:
        pythoncom.CoUninitialize()


def _enviar_via_smtp(
    destinatarios: Iterable[str],
    assunto: str,
    corpo_html: str,
    corpo_texto: str | None = None,
    anexos: Iterable[Path] | None = None,
    cc: Iterable[str] | None = None,
    bcc: Iterable[str] | None = None,
) -> None:
    cfg = _ler_config()

    destinatarios_list = [d.strip() for d in destinatarios if d and d.strip()]
    cc_list = [c.strip() for c in (cc or []) if c and c.strip()]
    bcc_list = [b.strip() for b in (bcc or []) if b and b.strip()]
    if not destinatarios_list:
        raise EmailConfigError("Lista de destinatários vazia")

    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = formataddr((cfg["from_name"] or "", cfg["from_addr"])) if cfg["from_name"] else cfg["from_addr"]
    msg["To"] = ", ".join(destinatarios_list)
    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    msg["Message-ID"] = make_msgid()

    msg.set_content(corpo_texto or _html_para_texto_simples(corpo_html))
    msg.add_alternative(corpo_html, subtype="html")

    for anexo in anexos or []:
        caminho = Path(anexo)
        if not caminho.exists():
            continue
        with open(caminho, "rb") as f:
            data = f.read()
        msg.add_attachment(
            data,
            maintype="application",
            subtype="octet-stream",
            filename=caminho.name,
        )

    todos_destinos = destinatarios_list + cc_list + bcc_list

    if cfg["use_ssl"]:
        contexto = ssl.create_default_context()
        with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=contexto, timeout=30) as s:
            s.login(cfg["user"], cfg["password"])
            s.send_message(msg, from_addr=cfg["from_addr"], to_addrs=todos_destinos)
    else:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as s:
            s.ehlo()
            if cfg["use_tls"]:
                contexto = ssl.create_default_context()
                s.starttls(context=contexto)
                s.ehlo()
            s.login(cfg["user"], cfg["password"])
            s.send_message(msg, from_addr=cfg["from_addr"], to_addrs=todos_destinos)


def _html_para_texto_simples(html: str) -> str:
    import re

    texto = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    texto = re.sub(r"</p>", "\n\n", texto, flags=re.IGNORECASE)
    texto = re.sub(r"</tr>", "\n", texto, flags=re.IGNORECASE)
    texto = re.sub(r"<[^>]+>", "", texto)
    return texto.strip()
