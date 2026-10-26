# U1 — u1-walking-skeleton — Plano de geração de código

Bolt: B2 | Unit: U1 (packaging) | Repo: `fazedordecodigo/bob` | Base: `main` @ `053dcaab7796f8885c4830ee3a5f6bf1fc75d65a` (conferido 2026-10-18 23:2x UTC-3; contém o #183 em `13a2792` e o #182)
Aprovação que abriu a U1: Emerson, via Maestro, 2026-10-18 23:11 (UTC-3): "Aprovo o checkpoint da U2. Vou fazer o merge do #183. Pode seguir para a U1."
Plan Approval deste plano: **pendente**. Nada despachado. Perguntas respondidas em 2026-10-19 02:46 UTC-3 (Q1 A, Q2 A): T6 entra; 6 PRs sequenciais.

## Summary
- Constrói o walking skeleton: `scripts/install.sh` (C01), `bob setup` (C02, `setup_cmd.py`), `install_project_skills` (C03), wheel com `plugin/` (C04), `user_dirs.py` (C13) e o harness `scripts/verify-install.sh` com espelho local de release (CT15).
- Toca: `src/bob_quality/{install_skills,setup_cmd,user_dirs,cli,messages}.py`, `src/bob_quality/plugin/` (3 symlinks), `pyproject.toml`, `scripts/{install.sh,verify-install.sh}`, `tests/{test_package,test_packaging,test_project_skills,test_setup_cmd,test_user_dirs,test_usage_exit,test_install_sh,test_verify_install}.py`, `CHANGELOG.md`; mais `.github/workflows/verify-install.yml` e o teste dele se Q1 = A.
- 6 tarefas (T1–T6; T6 entra porque Q1 = A), sequenciais, uma por PR.
- Prova: `pytest` (suíte inteira) + `sh scripts/verify-install.sh --only 1,2,3,4,7,8,9b` (passos 1, 2 parcial, 3, 4, 7, 8 parcial, 9b).

## Decisões fechadas
| # | Decisão | Escolha | Origem |
|---|---|---|---|
| D1 | Base | `main` @ `053dcaab`. Cada ET reconfere o HEAD no despacho; se mudou, o Arquiteto relê os arquivos da seção "Leia antes" antes de despachar. | conferência remota |
| D2 | Entrega | 6 PRs (T1–T6), um por tarefa, em sequência (Q2 = A). A próxima ET só é despachada depois do merge da anterior pelo Emerson. Checkpoint formal da U1 no fim (T6), com o harness verde na main. | DoD 2 (suíte verde em cada PR); Q2 confirma |
| D3 | Ordem | T1 (wheel) → T2 (skills no projeto) → T3 (`bob setup` + `BobHome`) → T4 (`install.sh`) → T5 (harness) → T6 (CI, se Q1 = A). Cada uma depende só das anteriores. | DAG das funções |
| D4 | Wheel | `src/bob_quality/plugin/` com 3 symlinks relativos versionados (`.claude-plugin`, `skills`, `LICENSE` → `../../../<nome>`). `package-data` ganha `plugin/.claude-plugin/plugin.json`, `plugin/skills/**/*`, `plugin/LICENSE`. Conferido no box (setuptools 84.0.0): `python -m build` segue os symlinks no sdist e no wheel. | ADR 0010; resolve o "Não verificado" da ADR no Linux |
| D5 | Fonte padrão das skills | `default_source()`: `PLUGIN_ROOT` se `PLUGIN_ROOT/.claude-plugin/plugin.json` é arquivo; senão `Path(__file__).resolve().parent / "plugin"`. `--source` passa a ter padrão `None` (= `default_source()`). | CT4 "Muda (v1)" |
| D6 | `SkillsResult` | Campos do CT4 + `unmarked: tuple[Path, ...] = ()` (pastas do manifesto sem `.bob-version`, para o aviso da regra 3). Acréscimo compatível. | CT4 regra 3; I13 |
| D7 | Escrita das skills | Cada pasta nasce num temporário irmão `.<nome>.bob-tmp-<pid>` e entra por `os.replace` (pasta antiga vai para `.<nome>.bob-old-<pid>` e é apagada depois). `.bob-version` é gravado dentro do temporário. | idempotência e falha parcial |
| D8 | Igualdade das skills | Igual = mesmo conjunto de caminhos relativos de arquivos (sem symlink) e mesmos bytes, contra o esperado: arquivos da skill + `LICENSE` de atribuição + `.bob-version`. | CT4 regra 2 |
| D9 | Duplicatas | Pasta `<nome>` do manifesto com `SKILL.md` em `.claude/skills` ou `.github/skills`, com ou sem `.bob-version` (o instalador antigo não gravava marcador). Só aviso. | CT4 regra 6 × ADR 0009; I10 |
| D10 | `_remove_retired` | Não é chamado por `install_project_skills` (é do CLI manual; imprime no stderr). | CT3 (passo não imprime) |
| D11 | `bob setup` × doctor | `STEPS` = `projeto`, `runtimes`, `npm`, `skills`. O doctor é fase final fixa, fora de `STEPS`, porque o código dele vira o código final e a saída dele é impressa. U3/U4/U5 inserem tuplas em `STEPS`. | CT3 × FR1.5; I11 |
| D12 | Impressão no `bob setup` | Linha de progresso `bob setup: <id>: ok` depois de cada passo ok; avisos como linha CT1 `bob setup: <id>: warning:`/`aviso: <texto>` logo depois; resumo no fim. O passo `npm` deixa passar a saída atual de `install_npm_dependencies` (fallback para cache, falha do `npm ci`). | CT1, CT3; I11 |
| D13 | Passo `npm` idempotente | Pula o `npm ci` quando `installed_npm_version(npm_prefix(), nome) == versão` para todo `pinned_npm_versions()`. | NFR4, U1-N4 |
| D14 | Piso do Python no `bob setup` | Lido de `importlib.metadata.metadata("bob-quality")["Requires-Python"]`, forma `>=A.B`. | ADR 0008 (fonte única) |
| D15 | `BOB_HOME` relativo no `bob setup` | Erro antes dos passos, com id `projeto`, exit 4, resumo com `bob doctor: not run`. | CT6 |
| D16 | Subcomando | `bob setup [--lang]`, sem `--config`, passa por `_blocked_config` como o `doctor`. Atualiza a lista fixa de `tests/test_usage_exit.py` (`_COMMANDS`, `_TOP_HELP`, `_SUB_HELP`). | CT3; conferido em `tests/test_usage_exit.py:215-266` |
| D17 | `install.sh`: fontes únicas | Topo do script, uma linha cada, regex `^NOME='(.*)'$`: `STEPS` (sem `perfil`), `DEFAULT_API`, `DEFAULT_DOWNLOAD`, `CURL_OPTS`, `PIP_OPTS`, `NODE_FLOOR='22.18.0'`, `NODE_BELOW='23'`, `PYTHON_FLOOR='3.10'`. `PROFILE_LINE` e `perfil` entram com o U6. | CT2, CT18; I9, I14 |
| D18 | `install.sh`: forma | `#!/bin/sh`, `set -u` (sem `-e`; erros tratados por passo), todas as funções antes, `main "$@"` como última linha (proteção contra `curl | sh` truncado). Mensagens en e pt-BR no próprio script. | CT2 |
| D19 | `install.sh`: 404 | No `download`, HTTP 404 tem mensagem própria ("a release <tag> está incompleta (<asset> ausente). Abra uma issue."), conforme CT14; outros erros usam a mensagem do CT2. | CT14 × CT2 |
| D20 | `install.sh`: `exec` | `exec "$BOB_HOME/bin/bob" setup --lang <l> </dev/null` (sem `BOB_INSTALL_PROFILE` até o U6; stdin fechado porque em `curl | sh` o stdin é o script). | CT2, CT3 |
| D21 | Testes do `install.sh` | Hermeticos: servidor HTTP local em thread (`http.server.ThreadingHTTPServer`), wheel sintético (`bob_quality-9.9.9-py3-none-any.whl` feito com `zipfile`, script `bob` que grava argv e sai com `$FAKE_BOB_RC`), stubs de `uname`, `node`, `npm`, `python3` quando preciso; `pip install` sem rede (wheel sem dependências). O e2e real fica no harness. | NFR14, tempo de CI |
| D22 | Harness: espelho | `<T>/mirror/` servido por `python3 -m http.server --bind 127.0.0.1 <porta livre>`: `api/releases/latest` (JSON), `download/<tag>/{install.sh,<wheel>,SHA256SUMS}`, `latest/download/<mesmos 3>` (one-liner), `bad/…` (wheel +1 byte, `SHA256SUMS` original), `prerelease/` e `draft/` fora do `latest`. Log do servidor em `<T>/mirror.log`. | CT12, CT15 |
| D23 | Harness: ambiente por passo | `env -i` com `HOME` novo, `TMPDIR`, `LANG=C.UTF-8`, `BOB_RELEASES_URL`, `PATH=<stubs do passo>:<fake-sudo>:<fixture-bin>:<NODE_DIR>:<PY_DIR>:/usr/bin:/bin`; repassa `PIP_*`, `npm_config_*`, `http(s)_proxy`, `no_proxy`, `SSL_CERT_FILE`, `SSL_CERT_DIR` se definidos. `PY_DIR` = `bin` do `sys.base_prefix` (não o venv). | CT15 × 2.6 (ordem do `PATH`); I12 |
| D24 | Harness: gitleaks | Fixture até o U3: tar.gz 8.30.1 da plataforma baixado uma vez para `${XDG_CACHE_HOME:-$HOME/.cache}/bob-verify-install/`, conferido pelo sha do CT9, extraído para `<T>/fixture-bin`. | pronto 1, CT9 |
| D25 | Harness: digest do projeto | sha256 + modo + alvo de symlink de cada caminho sob o projeto, exceto `.git/` (inclui `.git/hooks/`). | passos 1, 7, 8, 9b |
| D26 | Harness: ids | `STEP_IDS='1 2 3 4 7 8 9b'` no topo; `--only 9` = todos os `9*`. Passo 3 lê o `sudo.log` acumulado dos passos que rodaram (roda o passo 2 se ele não rodou). | CT15 |
| D27 | Harness: `VERIFY_REMOTE=1` | Sem espelho; `BOB_RELEASES_URL` não é definida; one-liner do GitHub; passo 9b imprime `verify-install: passo 9b: não se aplica (VERIFY_REMOTE=1)` e conta como ok. | CT6, CT15 |
| D28 | Mensagens do harness | Só pt-BR (ferramenta interna, como `install_skills`). Formato `verify-install: passo <n>: <motivo>`. | CT15 |
| D29 | Conteúdo exato | Especificação fechada nas ETs: assinaturas, regras, mensagens, testes Dado/Quando/Então, comandos, critérios. Sem corpo de função. | regra do Arquiteto |
| D30 | CHANGELOG | Dois parágrafos (en, pt-BR) no topo de `## Unreleased` por PR, no estilo da seção. | convenção do repo |
| D31 | Fora de escopo | `perfil` (U6), gitleaks no `bob setup` (U3), `bob.yaml` (U4), hook (U5), `bob --version`/`bob update` (U7), docs (U8), `release.yml` e matriz (U9). | units.md |

Decisões de produto respondidas: Q1 = A (harness no CI em todo PR, com a T6) e Q2 = A (um PR por tarefa, em sequência). Checkpoint: merge por PR pelo Emerson, com nota de verificação do Maestro; checkpoint formal no fim da U1, com o harness verde na main.

## Testing Contract
- Metodologia: TDD por tarefa. Os testes da seção "Testes a escrever" de cada ET vêm primeiro e falham na base; depois o código.
- Comando escopado à unit (cresce por tarefa; cada ET dá o seu): `python -m pytest -q tests/test_package.py tests/test_packaging.py tests/test_project_skills.py tests/test_user_dirs.py tests/test_setup_cmd.py tests/test_usage_exit.py tests/test_messages.py tests/test_install_sh.py tests/test_verify_install.py`.
- Regressão: `python -m pytest -q` → `0 failed`, `0 errors`.
- Cobertura: 100% das linhas novas/alteradas em `src/` (piso 80,0 mantido). CRAP < 10. Mutação: 0 sobreviventes sem waiver; 0 waivers novos.
- Ferramentas: as pinadas no repo (`build==1.6.1`, pytest, coverage, mutmut, lizard). Nenhuma dependência nova de runtime.
- Comando de Verificação: `sh scripts/verify-install.sh --only 1,2,3,4,7,8,9b` → exit 0 e 7 linhas `verify-install: passo <n>: ok` (T5). DoD 3 da U1 = esse comando.

## Passos
- [ ] P1. Wheel com `plugin/` e `default_source()` (T1; ADR 0010; pronto 9).
- [ ] P2. `install_project_skills` + `SkillsResult` (T2; CT4; FR3.1–3.4; ADR 0009, 0017).
- [ ] P3. `user_dirs.py` (`BobHome`, `bob_home`) (T3; CT5, CT6).
- [ ] P4. `setup_cmd.py` (`SetupContext`, `StepResult`, `STEPS`, `run_setup`), `bob setup` na CLI, chaves `setup.*` (T3; CT1, CT3; FR1.5, FR7.1, FR7.2).
- [ ] P5. `scripts/install.sh` e testes de paridade (T4; CT2, CT5, CT6, CT12, CT14; FR1.1–1.4, FR7.3; I9).
- [ ] P6. `scripts/verify-install.sh` com espelho local e passos 1, 2, 3, 4, 7, 8, 9b (T5; CT15).
- [ ] P7. Workflow `verify-install.yml` (T6; Q1 = A).
- [ ] P8. Em cada PR: comando escopado, suíte inteira, `bob check`, build + `twine check --strict`; checks verdes; merge do Emerson.
- [ ] P9. Depois do último merge: Arquiteto roda/confere o Comando de Verificação na `main`, fecha `trace.md` e `traceability.json`, e pede o checkpoint.

## Mecanismo de entrega
- Cada ET vai inteira e inline no prompt do cloud agent.
- Anexos: `functional-design.md` (esta pasta) e as seções do `inception/contracts/contract-summary.md` que a ET cita. Nada mais.
- Nada é despachado antes da Plan Approval (Q1/Q2 já respondidas).

## Tarefas
| Tarefa | Passos | Arquivos | Branch | Depende de |
|---|---|---|---|---|
| T1 — Levar skills, manifesto e LICENSE no wheel | P1, P8 | 8 (3 symlinks em `src/bob_quality/plugin/`, `pyproject.toml`, `install_skills.py`, `tests/test_package.py`, `tests/test_packaging.py`, `CHANGELOG.md`) | `aidlc/u1-walking-skeleton/t1-wheel-plugin` | nenhuma |
| T2 — Instalar as skills do projeto em `.agents/skills` com posse | P2, P8 | 3 (`install_skills.py`, `tests/test_project_skills.py`, `CHANGELOG.md`) | `aidlc/u1-walking-skeleton/t2-project-skills` | T1 |
| T3 — `bob setup` e pastas do usuário | P3, P4, P8 | 8 (`setup_cmd.py`, `user_dirs.py`, `cli.py`, `messages.py`, `tests/test_setup_cmd.py`, `tests/test_user_dirs.py`, `tests/test_usage_exit.py`, `CHANGELOG.md`) | `aidlc/u1-walking-skeleton/t3-bob-setup` | T2 |
| T4 — Comando único `scripts/install.sh` | P5, P8 | 3 (`scripts/install.sh`, `tests/test_install_sh.py`, `CHANGELOG.md`) | `aidlc/u1-walking-skeleton/t4-install-sh` | T3 |
| T5 — Harness `scripts/verify-install.sh` com espelho local | P6, P8 | 3 (`scripts/verify-install.sh`, `tests/test_verify_install.py`, `CHANGELOG.md`) | `aidlc/u1-walking-skeleton/t5-verify-install` | T4 |
| T6 — Harness no CI (Q1 = A) | P7, P8 | 3 (`.github/workflows/verify-install.yml`, `tests/test_verify_install_workflow.py`, `CHANGELOG.md`) | `aidlc/u1-walking-skeleton/t6-verify-install-ci` | T5 |

## Metas
U1-N1 ≤ 300 s; U1-N3 0 `sudo`; U1-N4 0 arquivos, 0 `npm ci`, 0 venv na 2ª execução; U1-N5 0 bytes; U1-N6 exit 4 e 0 venv; U1-N7 100%; U1-N9 3/0/0; U1-N10 5/5; U1-N12 ≤ 900 s; U1-N13 ≤ 60 s; U1-N14 0 failed, CRAP < 10, 0 sobreviventes, 100% das linhas novas (piso 80,0). Detalhe em `../nfr-requirements.md`.

## Autochecagem (antes do portão)
- [x] Cada critério de aceite das ETs é binário e tem comando ou leitura de arquivo.
- [x] Cada arquivo a criar/modificar tem a mudança descrita: assinaturas, tipos, regras, mensagens e testes. Sem corpo de função.
- [x] Sem "se necessário", "escolha a melhor forma", "como achar adequado".
- [x] Cada tarefa tem ≤ 8 arquivos e dependência explícita.
- [x] Nenhuma meta rebaixada: CRAP 10, cobertura 80,0, mutate sai 3, CI 3.10/3.12, gitleaks, `twine --strict` mantidos.
- [x] Decisões de produto/política foram para `code-generation-questions.md`, com recomendação.
