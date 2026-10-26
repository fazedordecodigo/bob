# Correção ET U7 T2 → v3 (2026-10-23, UTC-3)

## Motivo
PR rascunho #206 (head `ca859f0`). Após a v2 (teste 15), `bob check … mutate` deixou sobreviventes. O agente seguiu a ET: lista fechada → Bloqueios com testes propostos, sem improvisar e sem waiver. Lacuna da ET (lista incompleta + R7 com mutante equivalente), não falha de adesão. Sem mudança de decisão/ADR.

## Sobreviventes e resposta na v3
1. `_fetch` L101: `<` → `<=` no limiar HTTP 500 — novo teste **23** `test_http_500_is_retried`.
2. `_latest_tag` L115: `data = None` → `data = ""` no `except ValueError` — **equivalente** observável. **R7 v3:** no `ValueError` de `json.loads`, NÃO atribuir `data = None`; levantar de imediato `UpdateError(msg("update.api_failed", status=msg("update.bad_response")))`.
3. `_install` L170: `check=False` → `None`/omitido — teste **24** `test_install_passes_check_false`.
4. `_run` L195: `SetupContext` `home`/`lang`/`version` → `None` — teste **25** `test_setup_context_receives_home_lang_version`.
5. `cli._Version` L49: `default=argparse.SUPPRESS` → `None`/omitido — teste **26** `test_version_default_is_suppressed` (em `tests/test_update.py`).

## O que mudou
- R7: `ValueError` de `json.loads` → `UpdateError` imediato (sem `data = None`).
- Testes 23–26 na tabela; contagem **26 testes / 82 casos**; Comandos `176 passed` (82+79+5+10).
- Literais/Restrições: proibido `data = None` no except de R7; tabela de mutantes aponta 23–26.
- Cabeçalho Versão: v3; ver T2-v2.md.

## O que não muda
- Nenhuma decisão aprovada, ADR, R1–R6, R8–R16 (exceto o trecho R7 acima).
- Branch base `675d933`. Testes 1–22 e A1–A3 iguais (salvo alinhamento R7 no caso `not json` do 9, que continua com o mesmo stderr).
- `setup_cmd.py` continua proibido.

## Instrução de reply
Ajustar `update.py` só o necessário para R7 v3. Implementar testes 23–26 em `tests/test_update.py` conforme uploads/T2.md. Rodar de novo os Comandos a rodar. Limpar Bloqueios e tirar o PR de rascunho. Não fazer merge. Não waiver. Rodada 2/2.
