# Automacoes_CSA_Helibombas

Rotina comercial automatizada CSA® — peças Helibombas (Sectra + Outlook).

E-mails diários por operador, conferência semanal de markup/OBSINTERNA e relatórios avulsos.

---

## Instalação rápida

```powershell
git clone https://github.com/KaaioH013/Automacoes_CSA_Helibombas.git
cd Automacoes_CSA_Helibombas
py -3 -m pip install -r requirements.txt
copy .env.example .env
# Editar .env (banco + Outlook)
.\registrar_tarefas.bat
```

**Requisitos:** Windows, Python 3.10+, Outlook Classic logado (`EMAIL_BACKEND=outlook`).

---

## Tarefas agendadas

| Tarefa | Horário | Função |
|--------|---------|--------|
| `CSA_Rotina_Comercial_Manha_0800` | Seg–sex 08:00 | Rotina diária (Caio, Priscila, Patricia) |
| `CSA_Conferencia_Markup_Sexta_0815` | Sexta 08:15 | Conferência markup + OBSINTERNA (Caio) |

- Registrar: `registrar_tarefas.bat`
- Remover: `remover_tarefas.bat`
- Logs: `logs/`

---

## Envio manual (`.bat` na raiz)

| Arquivo | Uso |
|---------|-----|
| `rotina_comercial_manha.bat` | Rotina diária para os 3 operadores |
| `conferencia_markup_sexta.bat` | Conferência semanal |
| `preview_rotina_equipe.bat` | 3 previews só para comercial1 |
| `demonstrativo_30d.bat` | Panorama único 30 dias |
| `conferir_cotacoes.bat` | Cotações status A sem envio |
| `margem_cotacoes.bat` / `margem_pedidos.bat` | Markup baixo (avulso) |
| `produtividade_semanal.bat` | Produtividade |
| `margem_mes_operador.bat` | Margem do mês |

Padrão: **sem anexo Excel**. Opcional: `--com-anexo` nos scripts Python.

---

## Estrutura

```
automacoes_csa/          # pacote Python (SQL, HTML, regras, conexão, e-mail)
rotina_comercial_manha.py
conferencia_markup_sexta.py
enviar_*.py
registrar_tarefas.ps1
run_*.ps1
*.bat
```

---

## Regras de negócio

- Markup mínimo **1,40** (mesma lógica Analise_Cotacao)
- Rotina diária: markup do **dia útil anterior**; conferência de cotações **sem corte de data**
- Sexta: sex. passada + seg–qui; OBSINTERNA no cabeçalho; volume/dimensão não conta como justificativa
- Destinos: comercial1 / comercial6 / comercial4 (override: `COMERCIAL_PECAS_EMAILS`)

---

## Repositório legado

Este projeto foi extraído de [Acesso_servidor](https://github.com/KaaioH013/Acesso_servidor). Use **este** repo para a rotina comercial.
