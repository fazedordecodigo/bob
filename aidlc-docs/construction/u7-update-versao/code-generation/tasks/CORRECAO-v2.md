# Correção ET U7 T2 → v2 (2026-10-23, UTC-3)

## Motivo
PR rascunho #206. O teste 15 (`test_sh_failure`) da v1 fazia `monkeypatch.setattr(update.subprocess, "run", <sempre FileNotFoundError>)`. `update.subprocess` é o módulo stdlib compartilhado. `setup_cmd.step_projeto` chama `subprocess.run(["git", …])` antes do `sh` de R11c. Resultado: `setup.not_git_root` em vez de `update.install_failed`. Lacuna da ET, não do código de `update.py`.

## O que mudou
- Só a linha do teste 15: dublê seletivo. Falha só quando `argv[0] == "sh"`; outros argv vão para o `subprocess.run` real.
- Restrições: nota de que no teste 15 o `git` de `step_projeto` também é processo real.
- Cabeçalho Versão: v2.

## O que não muda
- Nenhuma decisão aprovada, ADR ou regra R1–R16.
- Branch base `675d933`. Contagem de casos: 78. Outros testes iguais.
- `setup_cmd.py` continua proibido.

## Instrução de reply
Alterar só `test_sh_failure` em `tests/test_update.py`. Rodar de novo os Comandos a rodar da ET. Tirar o PR de rascunho quando Bloqueios estiver vazio. Não fazer merge.
