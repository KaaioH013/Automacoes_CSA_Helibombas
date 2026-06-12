"""E-mail de aviso — rotina comercial diária para a equipe peças.

Envia para Caio, Priscila e Patricia (COMERCIAL_PECAS_EMAILS no .env).

Uso:
  python enviar_email_aviso_rotina_diaria.py
  python enviar_email_aviso_rotina_diaria.py --enviar
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from automacoes_csa.comum import destinatarios_equipe_pecas, proxima_segunda_rotina
from automacoes_csa.email_html import montar_email_aviso_rotina_diaria
from automacoes_csa.email_sender import EmailConfigError, enviar_email

load_dotenv()
EXPORT_DIR = Path("exports")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Aviso da rotina comercial diária para a equipe peças.")
    p.add_argument("--para", default=None, help="Destinatários (vírgula). Padrão: equipe peças")
    p.add_argument("--enviar", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    _, data_label = proxima_segunda_rotina()
    html = montar_email_aviso_rotina_diaria(data_label)

    EXPORT_DIR.mkdir(exist_ok=True)
    preview = EXPORT_DIR / "email_aviso_rotina_diaria.html"
    preview.write_text(html, encoding="utf-8")

    dests = destinatarios_equipe_pecas(args.para)
    print(f"Aviso rotina diária — início: {data_label}")
    print(f"Preview: {preview.resolve()}")
    print(f"Destinatários: {', '.join(dests)}")

    if not args.enviar:
        print("\nModo preview. Use --enviar para enviar.")
        return 0

    try:
        enviar_email(
            destinatarios=dests,
            assunto=f"[Aviso] Rotina comercial diária — a partir de {data_label}",
            corpo_html=html,
        )
        print("Enviado.")
    except EmailConfigError as e:
        print(f"[ERRO] {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
