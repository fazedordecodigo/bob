# U2 — u2-doctor-fonte-unica — Plano de geração de código

Bolt: B1 | Unit: U2 (library) | Repo: `fazedordecodigo/bob` | Base: `main` @ `d2e26bd1a75af1de48042af281ee418eb238fba8`
Aprovação que abriu a Construção: Emerson, 2026-10-18 20:28 UTC-3 ("Aprovo o 2.9 e o Comando de Verificação com os passos 1 a 14. Pode seguir para a Construção, começando pela U2.").
Plan Approval deste plano: **pendente**. Nada despachado.

## Summary
- Constrói: `pinned_npm_versions()`, `node_range()`, `NodeRange` e `PinSourceError` em `npm_tools.py`; o doctor lê as versões npm e o Node do `package.json` empacotado e as ferramentas npm só do prefixo do bob.
- Toca: `src/bob_quality/{npm_tools,doctor,messages}.py`, `tests/{test_npm_pin,test_doctor,test_ts_cli,test_gate_publications,test_action_workflow}.py`, `CHANGELOG.md` (9 arquivos, 1 tarefa).
- Testes: 22 testes novos (41 casos com parâmetros: 11 em `test_npm_pin.py`, 11 em `test_doctor.py`), 6 removidos (1 + 5), 6 reescritos em `test_doctor.py` (pins, `_assess*`), troca de `NODE` por `node_pin()` em 7 pontos; prova por `pytest` (I7).

## Decisões fechadas
| # | Decisão | Escolha | Origem |
|---|---|---|---|
| D1 | Caminho do `package.json` empacotado | `Path(os.path.abspath(__file__)).parent / "package.json"` em `npm_tools.py`. Mesmo padrão de `_plugin_packages()`; os testes já trocam `bob_quality.npm_tools.__file__`. | ADR 0008, código existente |
| D2 | Quando ler o Node | Sob demanda: `doctor.node_pin()`. Sai a constante `NODE`. | CT8 (refinamento técnico), CT1 (exit 4 + stderr); `cli.py` importa `doctor` no topo |
| D3 | Posição do Node em `PINS` | Marcador `NodeSlot()`; `_assess` recebe `_Expected(python, npm, node)`. | D2 |
| D4 | Forma de `NpmPin` | `NpmPin(name, npm_package)`. Saem `expected` e `executable`. | CT8, ADR 0019 |
| D5 | Onde ler a versão npm encontrada | Só `<npm_prefix()>/node_modules/<pacote>/package.json`. Sem fallback para `--version` no `PATH`. | ADR 0019 |
| D6 | Onde achar executáveis | `_locate = shutil.which(executable)`. Sem `cwd/node_modules/.bin`. | I5, ADR 0019 |
| D7 | Mensagens | Chaves `npm.pin_source`, `npm.pin_not_json`, `npm.pin_not_object`, `npm.pin_not_exact`, `npm.pin_bad_node_range`, `doctor.error`, em `_EN` e `_PT_BR`. Linha final `bob doctor: package.json: … Reinstale o bob.` | CT1, CT8 |
| D8 | Hermeticidade dos testes de CLI | `_run_doctor` aponta `XDG_CACHE_HOME` para um prefixo falso completo (cópia do `package.json` da raiz + `node_modules/<pacote>/package.json`). `npm_prefix()` já prefere esse cache quando ele bate. | código existente (`_cache_ready`) |
| D9 | Versões npm nos testes | `test_doctor.py` e `test_ts_cli.py` leem do `package.json`; `test_npm_pin.py` usa só versões sintéticas. | Pronto 1, U2-N4 |
| D10 | Quebra em tarefas | 1 tarefa (T1), 9 arquivos. Passa de ~8 por 1: 4 arquivos têm 2 a 5 linhas de troca de import. Quebrar deixaria a suíte vermelha entre PRs. | skill plano-de-geracao-de-codigo, DoD 2 |
| D11 | Conteúdo exato | Especificação fechada em `tasks/T1.md`: assinaturas, tipos, regras R1–R9, mensagens en/pt-BR, códigos de saída, testes Dado/Quando/Então e lista fechada dos 9 arquivos. Sem código de implementação; o código é escrito pelo cloud agent. | regra do Arquiteto, skill especificacao-de-tarefa-para-agente-de-codigo |
| D12 | CHANGELOG | Dois parágrafos (en, pt-BR) no topo de `## Unreleased`, no estilo da seção. | convenção do repo |
| D13 | Fora de escopo | Docs com `5.0.4` (U8); mocks de `tests/test_coverage_slots.py`; erro de mypy pré-existente em `_string_version`; teste de paridade com `install.sh` (U1, I9). | units.md, I7 |

Decisão de produto pendente: nenhuma. Sem `code-generation-questions.md`.

## Testing Contract
- Metodologia: TDD por tarefa. Testes de `tasks/T1.md` → "Testes a escrever" primeiro; confirmar que falham (ImportError ou assert) na base; depois o código.
- Comando escopado à unit: `python -m pytest -q tests/test_npm_pin.py tests/test_doctor.py tests/test_ts_cli.py tests/test_gate_publications.py tests/test_action_workflow.py tests/test_messages.py`.
- Regressão: `python -m pytest -q` (suíte inteira) → `0 failed`, `0 errors`.
- Cobertura: 100% das linhas alteradas em `src/` (piso do repo 80,0 mantido). CRAP < 10 por função alterada. Mutação: 0 sobreviventes sem waiver.
- Ferramentas: pytest 9.1.1, coverage 7.16.2, mutmut 3.8.0, lizard 1.24.1 (versões pinadas do repo). Nenhuma dependência nova.
- Comando de Verificação: só `pytest` para a U2 (I7). O passo 8 do harness é da U1; `scripts/verify-install.sh` não existe. DoD 3 = N/A.

## Passos
- [ ] P1. Testes de fonte única e paridade em `tests/test_npm_pin.py` (FR2.1, ADR 0008; Pronto 1 e 3).
- [ ] P2. Testes de doctor em `tests/test_doctor.py`: prefixo do bob, vitest do projeto ignorado, `.bin` do projeto ignorado, vitest 5.0.5, stderr en/pt-BR, 2 subprocessos, `node_pin` (US1.4 crit. 2, FR2.5, NFR5, FR1.5; Pronto 2 e 4).
- [ ] P3. Ajustar consumidores de `NODE` e versões fixas: `test_gate_publications.py`, `test_action_workflow.py`, `test_ts_cli.py` (FR2.1).
- [ ] P4. `npm_tools.py`: `PinSourceError`, `NodeRange`, `pinned_npm_versions()`, `node_range()` (CT8; FR2.1).
- [ ] P5. `messages.py`: 6 chaves em en e pt-BR (CT1, NFR9).
- [ ] P6. `doctor.py`: `NpmPin(name, npm_package)`, `NodeSlot`, `node_pin()`, `_Expected`, `_report_pins` com `PinSourceError`, leitura só do prefixo, `_locate` só no `PATH` (US1.4, FR2.5, NFR5, ADR 0019).
- [ ] P7. `CHANGELOG.md` en + pt-BR (DoD 5).
- [ ] P8. Rodar o comando escopado, a suíte inteira, `rg` de literais, `bob doctor`, build + `twine check --strict`, `bob check` (DoD 1, 2; Pronto 1–5).
- [ ] P9. PR com título e corpo da ET; checks verdes; merge pelo Emerson; Arquiteto confere o job `package` na `main` (DoD 6; Pronto 5).

## Mecanismo de entrega
- A ET `tasks/T1.md` vai inteira e inline no prompt do cloud agent.
- Anexos: só os artefatos de design que a ET manda ler e que não estão no repo: `functional-design.md` (esta pasta) e `inception/contracts/contract-summary.md` (seções CT1 e CT8).
- Nenhum outro anexo. Despacho só depois da Plan Approval, com aviso do Maestro.

## Tarefas
| Tarefa | Passos | Arquivos | Depende de |
|---|---|---|---|
| T1 — Ler as versões npm do package.json empacotado no bob doctor | P1–P9 | 9 (lista em `tasks/T1.md`) | nenhuma |

## Autochecagem (antes do portão)
- [x] Cada critério de aceite da ET é binário e tem comando ou leitura de arquivo.
- [x] Cada arquivo a modificar tem a mudança exata descrita na ET: assinaturas, tipos, regras, mensagens, posições e testes. Sem corpo de função.
- [x] Sem "se necessário", "escolha a melhor forma", "como achar adequado".
- [x] Nenhuma meta rebaixada: CRAP 10, cobertura 80,0, mutate sai 3, CI 3.10/3.12, gitleaks, `twine --strict` mantidos.
