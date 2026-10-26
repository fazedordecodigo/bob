# U3 — u3-gitleaks — Plano de geração de código

Bolt: B3 | Unit: U3 (library) | Repo: `fazedordecodigo/bob` | Base: `main` @ `387b0b6d0b19907e02b0db78762d6d8656e7135c` (conferida com `get_branch` em 2026-10-19 22:3x UTC-3; contém o #190, último PR da U1)
Aprovação que abriu a U3: Emerson, via Maestro, 2026-10-19 22:44 (UTC-3): "Aprovo o checkpoint da U1. Pode seguir para a U3."
Plan Approval deste plano: **pendente**. Nada despachado. Perguntas respondidas em 2026-10-19 23:10 UTC-3 ("Q1 A, Q2 A."): Q1 = A (I15: mantém `--retry 2`, CT14 ajustado); Q2 = A (T4 entra na U3).

## Summary
- Constrói o C07 (`src/bob_quality/gitleaks.py`): tabela dos 4 assets e sha256 (ADR 0014), `platform_key`, `ensure_gitleaks` com download, sha256, extração segura e instalação atômica em `BOB_HOME` (CT5, CT9). Estende o C02 (passo `gitleaks` do `bob setup`, CT3 ordem 4) e o C08 (`bob doctor` procura em `BOB_HOME/bin` antes do `PATH`; `--install` também instala o gitleaks; CT8). Tira a fixture do harness e acrescenta o passo 9a (CT15).
- Toca: `src/bob_quality/{gitleaks,messages,setup_cmd,doctor,user_dirs}.py`, `scripts/verify-install.sh`, `tests/{test_gitleaks,test_setup_cmd,test_doctor,test_user_dirs,test_verify_install}.py`, `CHANGELOG.md`, `src/bob_quality/secrets_gate.py`, `tests/test_secrets_scan.py`.
- 4 tarefas (T1–T4), sequenciais, um PR por tarefa.
- Prova: `pytest` (suíte inteira) + `sh scripts/verify-install.sh --only 2,7,9a` (pronto 2, 3 e 4 da U3) e o harness inteiro no job `verify-install / linux-x64`.

## Decisões fechadas
| # | Decisão | Escolha | Origem |
|---|---|---|---|
| D1 | Base | `main` @ `387b0b6d`. Cada ET reconfere o HEAD no despacho; se mudou, o Arquiteto relê os arquivos de "Leia antes". | conferência remota |
| D2 | Entrega | Um PR por tarefa, em sequência; a próxima ET só sai depois do merge da anterior pelo Emerson. Checkpoint da U3 no fim, com o harness verde na `main`. | política da U1 (Q2 = A da U1, 2026-10-19 02:46) |
| D3 | Ordem | T1 (`gitleaks.py`) → T2 (`bob setup` + doctor) → T3 (harness) → T4 (gate `secrets`; Q2 = A). T2 não quebra o harness: até a T3, o `bob setup` baixa do GitHub (sem `BOB_GITLEAKS_BASE_URL`) e a fixture ainda está no `PATH`. | DAG das funções |
| D4 | Chave de `ASSETS` | `(system, arch)` com `system` ∈ {`linux`, `darwin`} (minúsculo, igual ao nome do asset) e `arch` ∈ {`x64`, `arm64`}. | CT9 (só fixa `arch`) |
| D5 | Reuso | `installed_version(home)`: roda `home.bin/"gitleaks" --version` (timeout 30 s, stdin fechado); devolve a 1ª ocorrência de `\d+\.\d+\.\d+(?:-[0-9A-Za-z.]+)?` no stdout; `None` se não existe, não roda, sai ≠ 0 ou não tem versão. Reusa só se `== "8.30.1"`. Mais estrito que o "contém" do CT9 (recusa `8.30.1-beta.1` e `8.30.10`). | CT9, R7 |
| D6 | Download | `urllib.request.urlopen(url, timeout=30)`, `response.read()` inteiro, depois grava `<tmp>/<asset>`. Até 3 tentativas; retry só em `HTTPError` com código ≥ 500 e em erro de rede (`URLError` sem HTTP, `TimeoutError`, `ConnectionError`, `http.client.HTTPException`); `time.sleep(1.0)` antes de cada retry. `{status}` = `HTTP <código>` ou o nome da classe da causa. | CT14, R9 |
| D7 | Extração | `tarfile.open(path, "r:gz")`; exatamente um membro com `name == "gitleaks"` e `isreg()`; bytes por `extractfile`. Nada de `extract`/`extractall`. `tarfile.TarError`, `EOFError`, `zlib.error` e `OSError` ao ler o arquivo → extração. | CT9, R4 |
| D8 | Instalação | R5 + R6 do `functional-design.md`. Link relativo `../tools/gitleaks/8.30.1/gitleaks`. | CT5, CT9 |
| D9 | Acréscimos ao CT9 | `DEFAULT_BASE_URL`, `base_url(env)`, `asset_url(key, base)`, `installed_version(home)`; mensagens `gitleaks.url_not_allowed` e `gitleaks.write`. Compatíveis (nenhum nome do CT9 muda). | CT9 lista 4 erros; R6, R8 pedem 2 |
| D10 | Passo `gitleaks` | `step_gitleaks(ctx)`: `installed_version == VERSION` → `unchanged` sem chamar `ensure_gitleaks`; senão `ensure_gitleaks(ctx.home)` → `installed` com `setup.item_gitleaks`; `GitleaksError` → `failed` com `reason(exc)`. Inserido entre `npm` e `skills`. | CT3 ordem 4 |
| D11 | Pin do doctor | `BinaryPin` com os mesmos 5 campos; valores vêm de `gitleaks.VERSION`, `gitleaks.asset_url(("linux", "x64"))` e `gitleaks.ASSETS[("linux", "x64")][1]`. Dica de instalação sem mudança (asset linux_x64). | ADR 0014; workflows conferem esse par |
| D12 | Busca de binários | `user_dirs.locate_binary(name, env=os.environ) -> str \| None`: `bob_home(env).bin / name` se `is_file()` e `os.access(…, os.X_OK)`; senão `shutil.which(name)` com um argumento só; `BOB_HOME` relativo (`ValueError`) → só `PATH`. `doctor._locate` passa a chamar essa função (vale para `node` e `gitleaks`). | CT8 "U3 acrescenta", ADR 0019 |
| D13 | `doctor --install` | R12. `BOB_HOME` relativo → `bob doctor: BOB_HOME=<v> must be absolute. Use an absolute path.` e `4` (chave nova `doctor.bob_home_relative`). | CT8 |
| D14 | Testes herméticos | `tests/test_doctor.py` ganha fixture `autouse` que faz `monkeypatch.setenv("BOB_HOME", str(tmp_path / "bob-home"))` (pasta vazia); o `_run_doctor` herda pelo `os.environ.copy()`. T4 faz o mesmo em `tests/test_secrets_scan.py`. | um `BOB_HOME/bin/gitleaks` real na máquina do dev não pode mudar o resultado |
| D15 | Testes de `gitleaks.py` | Servidor `http.server.ThreadingHTTPServer` em thread em `127.0.0.1:0`, com tabela caminho → (status, bytes) e log de pedidos; tar.gz sintético feito com `tarfile` em memória, membro `gitleaks` = script `sh` que imprime `8.30.1` para `version` e `gitleaks version 8.30.1` para o resto; `monkeypatch` em `gitleaks.platform_key`, `gitleaks.ASSETS`, `tempfile.tempdir` e `gitleaks.time.sleep`. Nenhum acesso à internet. | NFR14, D21 da U1 |
| D16 | Harness: espelho e `PATH` | R13. Globais novas `GL_ASSET` e `GL_URL`; `run_oneliner` repassa `BOB_GITLEAKS_BASE_URL=$GL_URL` se não vazia e falha o passo se o `PATH` do passo tem `gitleaks`. `tool_path` = `$T/fake-sudo:$NODE_DIR:$PY_DIR:/usr/bin:/bin`. | pronto 2, CT15 |
| D17 | Harness: passos 2, 7, 9a | Tabela "Harness" do `functional-design.md`. `STEP_IDS='1 2 3 4 7 8 9a 9b'`; `--only 9` = `9a 9b`. | verification-command passos 2, 7, 9 |
| D18 | Harness: `VERIFY_REMOTE=1` | `prepare_gitleaks` não roda; `GL_URL` vazia (o `bob setup` baixa do GitHub); 9a imprime `verify-install: passo 9a: não se aplica (VERIFY_REMOTE=1)`. Passo 2 confere link e versão nos dois modos; contagem de pedidos só no espelho. | D27 da U1 |
| D19 | Harness: constantes | Mantém `GITLEAKS_VERSION` e os 4 `GITLEAKS_SHA_*` (o shell não importa a tabela Python); teste confere igualdade com `gitleaks.ASSETS`. | ADR 0014 (fonte única no código do produto; harness é teste) |
| D20 | I15 | A U3 não muda `install.sh` nem `CURL_OPTS`. O `gitleaks.py` segue a regra Python do CT14 (sem retry em `4xx`, inclusive `429`). Q1 = A: CT14 ajustado no texto (429 até 2 retries só no `curl`; 403 nunca). | Q1 = A; seção I15 abaixo |
| D21 | CHANGELOG | Dois parágrafos (en, pt-BR) no topo de `## Unreleased` por PR. | convenção do repo |
| D22 | Largura de linha | `.py`: linhas novas ≤ 100 colunas (exceção: docstring de texto exato). Shell e Markdown no estilo dos vizinhos. | lição da T2 da U1 |
| D23 | Conteúdo exato | ETs fechadas: assinaturas, regras, mensagens, testes Dado/Quando/Então, comandos, critérios. Sem corpo de função. | regra do Arquiteto |
| D24 | Fora de escopo | Bloco 11 do prompt e paridade (U8); matriz (U9); `bob --version` (U7); dica do doctor por plataforma; texto `cli.setup`; mudar `CURL_OPTS`. | units.md, D20 |

## Testing Contract
- Metodologia: TDD por tarefa. Os testes de "Testes a escrever" vêm primeiro e falham na base; depois o código.
- Comando escopado à unit: `python -m pytest -q tests/test_gitleaks.py tests/test_setup_cmd.py tests/test_doctor.py tests/test_user_dirs.py tests/test_messages.py tests/test_verify_install.py` (+ `tests/test_secrets_scan.py tests/test_check_dispatch.py` com a T4).
- Regressão: `python -m pytest -q` → `0 failed`, `0 errors` (linha de base: `main` @ `387b0b6`, 4322 passed no head do #190).
- Cobertura: 100% das linhas novas/alteradas em `src/` (piso 80,0 mantido). CRAP < 10. Mutação: 0 sobreviventes sem waiver; 0 waivers novos.
- Ferramentas: as pinadas no repo. Nenhuma dependência nova (só stdlib: `urllib`, `tarfile`, `hashlib`, `tempfile`, `platform`).
- Comando de Verificação da U3: `sh scripts/verify-install.sh --only 2,7,9a` → exit 0 e 3 linhas `verify-install: passo <n>: ok` (T3). O harness inteiro (8 passos) roda no check `verify-install / linux-x64` de cada PR.

## Passos
- [ ] P1. `gitleaks.py`: tabela, `platform_key`, `base_url`, `asset_url`, `installed_version`, `ensure_gitleaks`; chaves `gitleaks.*` (T1; CT9, CT14; FR2.2, FR2.3; pronto 1).
- [ ] P2. `user_dirs.locate_binary` e doctor: pin da tabela, busca em `BOB_HOME/bin`, `--install` com gitleaks (T2; CT8; ADR 0014, 0019).
- [ ] P3. Passo `gitleaks` no `bob setup` (T2; CT3; US1.3).
- [ ] P4. Harness sem fixture; passos 2 e 7 com as checagens do gitleaks; passo 9a (T3; CT15; pronto 2, 3, 4).
- [ ] P5. Gate `secrets` com `locate_binary` (T4; CT8, ADR 0019; FR2.1; Q2 = A).
- [ ] P6. Em cada PR: comando escopado, suíte inteira, `bob check`, checks verdes (6: `CI / pytest (3.10)`, `CI / pytest (3.12)`, `package / dist`, `bob / check`, `bob / cold`, `verify-install / linux-x64`); merge do Emerson.
- [ ] P7. Depois do último merge: Arquiteto confere o harness na `main` (run do `verify-install` no push), fecha `trace.md` e `traceability.json` e pede o checkpoint.

## Mecanismo de entrega
- Cada ET vai inteira e inline no prompt do cloud agent.
- Anexos: `functional-design.md` (pasta da U3) e as seções do `inception/contracts/contract-summary.md` que a ET cita. Nada mais.
- Nada é despachado antes da Plan Approval (Q1/Q2 já respondidas).

## Tarefas
| Tarefa | Passos | Arquivos | Branch | Depende de |
|---|---|---|---|---|
| T1 — Módulo `gitleaks.py`: tabela, download conferido e instalação em `BOB_HOME` | P1, P6 | 4 (`src/bob_quality/gitleaks.py`, `src/bob_quality/messages.py`, `tests/test_gitleaks.py` com 32 testes, ET v2, `CHANGELOG.md`) | `aidlc/u3-gitleaks/t1-gitleaks-module` | nenhuma |
| T2 — Passo `gitleaks` no `bob setup` e doctor com `BOB_HOME/bin` | P2, P3, P6 | 8 (`src/bob_quality/{setup_cmd,doctor,user_dirs,messages}.py`, `tests/{test_setup_cmd,test_doctor,test_user_dirs}.py`, `CHANGELOG.md`) | `aidlc/u3-gitleaks/t2-setup-doctor` | T1 |
| T3 — Harness sem fixture do gitleaks e passo 9a | P4, P6 | 3 (`scripts/verify-install.sh`, `tests/test_verify_install.py`, `CHANGELOG.md`) | `aidlc/u3-gitleaks/t3-verify-install` | T2 |
| T4 — Gate `secrets` acha o gitleaks de `BOB_HOME/bin` | P5, P6 | 3 (`src/bob_quality/secrets_gate.py`, `tests/test_secrets_scan.py`, `CHANGELOG.md`) | `aidlc/u3-gitleaks/t4-secrets-gate` | T3 |

## Metas
U3-N1 ≤ 300 s; U3-N3 exit 4, 0 em `tools/gitleaks`, 1 GET; U3-N4 0 GETs e mtime igual; U3-N5 ≤ 60 s; U3-N6 4/4; U3-N7 1 arquivo; U3-N8 100%; U3-N9 30 s/3/1/0; U3-N10 0/0/0; U3-N11 0; U3-N13 ≤ 900 s; U3-N15 0 failed, CRAP < 10, 0 sobreviventes, 100% das linhas novas (piso 80,0). Detalhe em `../nfr-requirements.md`.

## I15 — CT14 × `CURL_OPTS` (`--retry 2` no `429`): decidida A
**Decisão:** A — Emerson, via Maestro, 2026-10-19 23:10 UTC-3: "Q1 A, Q2 A." O `CURL_OPTS` do `install.sh` (CT18) fica com `--retry 2`, sem mudança de código e sem PR. O texto do CT14 foi ajustado em 2026-10-19 23:1x UTC-3: no lado `install.sh`/`curl`, `429` pode ser repetido até 2 vezes e `403` nunca é repetido; no lado Python (`gitleaks.py`, `bob update`), `4xx`, inclusive `429`, sem retry. A U3 não muda `install.sh` (D20). Nota de alteração no "Registro" do `contract-summary.md`.

**Contexto (registro da proposta).** O CT14 dizia, para `GET …/releases/latest`: "`403`/`429` = limite → sem retry". O `curl --retry` repete timeout e HTTP `408`, `429`, `500`, `502`, `503`, `504`; não repete `403`. O curl ≥ 7.66 respeita o `Retry-After` do `429` (espera não medida).

| Opção | O que mudava | Prós | Contras |
|---|---|---|---|
| **A. Manter `--retry 2` e ajustar o texto do CT14 (escolhida)** | Só o texto do CT14. | Zero código e zero PR; fonte única do CT18 e paridade da U8 mantidas; `403` (caso comum) já sem retry. | Até 2 pedidos extras no `429`; `Retry-After` alto pode pesar no NFR1. |
| B. `curl` da API sem `--retry`, retry manual em rede/`5xx` | `install.sh`, `test_install_sh.py`, CT18 com 2 variáveis; +1 PR. | Comportamento literal do CT14 antigo. | Mais shell num arquivo já mergeado; quebra a fonte única. |
| C. `--retry 2 --retry-max-time 30` | 1 linha do `install.sh` e o bloco 11 do CT18. | Teto de tempo; fonte única mantida. | Ainda repete o `429`; semântica com `Retry-After` não conferida. |

## Autochecagem (antes do portão)
- [x] Cada critério de aceite das ETs é binário e tem comando ou leitura de arquivo.
- [x] Cada arquivo a criar/modificar tem a mudança descrita: assinaturas, tipos, regras, mensagens e testes. Sem corpo de função.
- [x] Sem "se necessário", "escolha a melhor forma", "como achar adequado".
- [x] Cada tarefa tem ≤ 8 arquivos e dependência explícita.
- [x] Nenhuma meta rebaixada: CRAP 10, cobertura 80,0, mutate 0 sobreviventes, CI 3.10/3.12, gitleaks no CI, harness ≤ 900 s, passo 2 ≤ 300 s, passo 7 ≤ 60 s.
- [x] Decisões de produto/política foram para `code-generation-questions.md`, com recomendação.
