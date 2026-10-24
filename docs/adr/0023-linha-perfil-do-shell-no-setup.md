# Linha `perfil do shell` no resumo do `bob setup`

Status: aceita pelo Emerson em 22/10/2026, no Plan Approval da U6, da U7 e da U8. Publicada em `docs/adr/` na U9.

## Decisão

A função privada `setup_cmd._profile_text(value)` mapeia o valor de `BOB_INSTALL_PROFILE`:
- `already-on-path` → `setup.profile_on_path`;
- `already-marked:/…` → `setup.profile_marked`;
- `failed:/…` → `setup.profile_failed`;
- `/…` → `setup.profile_added`;
- vazio, ausente, relativo ou outro valor → nada.

A linha (`setup.profile`) sai em `_summary`, antes de `  bob doctor:`, também no resumo parcial (`_fail`). Lê `os.environ` dentro de `_summary`. As chaves novas entram em `messages.py` logo depois de `setup.doctor_not_run` (en e pt-BR).

## Consequências

Nada muda sem a variável: os testes atuais do resumo seguem iguais. Os textos en são tradução dos pt aprovados no CT3.
