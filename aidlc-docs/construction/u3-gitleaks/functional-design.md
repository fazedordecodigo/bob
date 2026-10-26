# U3 — u3-gitleaks — Desenho funcional (3.1, Standard)

Unit: U3 | Kind: library | Dona de: C07 (`src/bob_quality/gitleaks.py`) | Estende: C02 (passo `gitleaks` do `bob setup`), C08 (`bob doctor`), gate `secrets` (T4, Q2 = A), C15 (harness, passos 2, 7 e 9a)
Contratos de que é dona: CT9. Consome: CT1, CT3, CT5, CT6, CT14, CT15 (U1); CT8 (U2, acrescenta o trecho "U3 acrescenta").
ADR: 0014 (tabela de sha256 só no código), 0019 (binários primeiro em `BOB_HOME/bin`, depois `PATH`).
Histórias e requisitos: US1.3 (dona), US1.1 crit. 1 e 5 (contribui); FR2.2, FR2.3; NFR1, NFR3, NFR6, NFR9.
Base lida: `fazedordecodigo/bob` `main` @ `387b0b6d0b19907e02b0db78762d6d8656e7135c` (#190 mergeado; leitura remota pontual, sem clone). Data: 2026-10-19 22:5x (UTC-3).

## O que passa a existir
O `bob setup` baixa o gitleaks 8.30.1 da plataforma, confere o sha256 contra a tabela do código, extrai só o binário e liga `BOB_HOME/bin/gitleaks`. Na 2ª execução, nada é baixado. O `bob doctor` acha esse binário antes do `PATH`, e o `bob doctor --install` também instala o gitleaks. O harness para de pôr o gitleaks no `PATH` (fim da fixture D24 da U1) e ganha o passo 9a (tar.gz adulterado).

```
bob setup: projeto → runtimes → npm → gitleaks → skills → [doctor] → resumo
  gitleaks: BOB_HOME/bin/gitleaks --version = 8.30.1? → unchanged (0 downloads)
            senão: plataforma → URL → download (temp) → sha256 → extrai "gitleaks" → tools/gitleaks/8.30.1/gitleaks (0755) → bin/gitleaks (link)
```

## Estado atual do repo (conferido @ 387b0b6)
| Ponto | Hoje | Onde |
|---|---|---|
| Módulo gitleaks | não existe (`src/bob_quality/gitleaks.py` ausente) | árvore da `main` |
| Pin do gitleaks no doctor | `BinaryPin("gitleaks", "8.30.1", "gitleaks", <url linux_x64>, "551f…70eb")` com literais | `doctor.py:91-97` |
| Busca de binários no doctor | `_locate = shutil.which` (só `PATH`) | `doctor.py:413-414` |
| `bob doctor --install` | só `install_npm_dependencies` | `doctor.py:132-136` |
| `bob setup` | `STEPS = (projeto, runtimes, npm, skills)` | `setup_cmd.py:175-180` |
| `BobHome` | já tem `bin` e `tools` | `user_dirs.py` |
| `ToolError` | `class ToolError(Exception)` | `tools.py` |
| Gate secrets (`bob check --gates secrets`) | `shutil.which("gitleaks")`; ausente → `tool.missing`, exit 4 | `secrets_gate.py:125-127` |
| Harness | fixture: baixa o tar.gz, confere, extrai para `$T/fixture-bin` e põe no `PATH`; `STEP_IDS='1 2 3 4 7 8 9b'`; `run_oneliner` não repassa `BOB_GITLEAKS_BASE_URL` | `scripts/verify-install.sh:5-10`, `:390-392`, `:556-612`, `:353-388` |
| Testes ligados ao pin | `test_gitleaks_constants_match_the_doctor_pin`, `test_step_ids_are_the_u1_steps`, `_HELP` | `tests/test_verify_install.py` |
| Testes ligados aos passos | `test_steps_are_the_u1_steps_in_order`; `test_setup_does_not_touch_the_project_package_files` roda os `STEPS` reais | `tests/test_setup_cmd.py:288-289`, `:892-920` |
| Binário oficial | `gitleaks version` → `8.30.1`; `gitleaks --version` → `gitleaks version 8.30.1`; tar.gz linux_x64 com `LICENSE`, `README.md`, `gitleaks` (0755) na raiz; sha256 `551f…70eb` | conferido no box em 2026-10-19 22:4x (UTC-3) |

## Regras de negócio
| # | Regra | Origem |
|---|---|---|
| R1 | A tabela dos 4 assets e sha256 existe só em `gitleaks.py` (`ASSETS`). `doctor.py` e `setup_cmd.py` importam dela. Nenhum `checksums.txt` é baixado. | ADR 0014, CT9 |
| R2 | Plataforma fora da tabela → `GitleaksError` plataforma, antes de qualquer requisição. | CT9, NFR3 |
| R3 | Nenhum byte baixado sai do temporário antes de o sha256 bater com a tabela. Falha de sha → `GitleaksError` integridade; `BOB_HOME/tools/gitleaks` e `BOB_HOME/bin/gitleaks` não são criados. | FR2.3, NFR6, US1.3 crit. 1 e 2 |
| R4 | Do tar.gz só sai o membro de nome exato `gitleaks`, arquivo regular, único. Qualquer outra forma (ausente, link, em subpasta, `./gitleaks`, duplicado, arquivo que não é gzip/tar) → `GitleaksError` extração; nada instalado. | CT9 |
| R5 | Instalação atômica: grava `tools/gitleaks/8.30.1/gitleaks.tmp`, `chmod 0755`, `os.replace` para `gitleaks`; o link `bin/gitleaks` (alvo relativo `../tools/gitleaks/8.30.1/gitleaks`) nasce como `bin/gitleaks.tmp` e entra por `os.replace`. | CT5, CT9 |
| R6 | Falha de escrita (`OSError`) na instalação → `GitleaksError` escrita; apaga `gitleaks.tmp` e `bin/gitleaks.tmp`; se `tools/gitleaks` não existia antes da chamada, apaga `tools/gitleaks` inteiro. | CT9 ("nada fica em `tools/gitleaks`") |
| R7 | Reuso: `BOB_HOME/bin/gitleaks` existe e a 1ª versão `X.Y.Z[-pre]` da saída de `--version` é exatamente `8.30.1` → nada é baixado nem escrito. Versão diferente, pré-release, link quebrado ou binário que não roda → reinstala. | CT9, NFR4, pronto 4 |
| R8 | URL = `<base>/<asset>`. `base` = `BOB_GITLEAKS_BASE_URL` sem UMA barra final, se definida e não vazia; senão `https://github.com/gitleaks/gitleaks/releases/download/v8.30.1`. Base precisa casar `https://*`, `http://127.0.0.1`, `http://127.0.0.1[:/]*`, `http://localhost` ou `http://localhost[:/]*` (mesma regra do `BOB_RELEASES_URL`, R10 da T4 da U1); senão `GitleaksError` URL. | CT6, CT18 bloco 11 |
| R9 | Rede: `urllib.request.urlopen(…, timeout=30)` por tentativa; até 3 tentativas (2 retries) só em erro de rede ou HTTP `5xx`, com pausa de 1 s antes de cada retry; `4xx` (inclusive `429`) e erro de sha/extração não repetem. | CT14 |
| R10 | Nenhum `print` em `gitleaks.py`. Erros são `GitleaksError(msg(...))` com texto CT1 (`gitleaks: <falha>. <ação>.`), en e pt-BR no catálogo. | CT1, CT3, NFR9 |
| R11 | `bob doctor` e o gate `secrets` (T4) procuram binários primeiro em `BOB_HOME/bin/<nome>` (arquivo executável), depois no `PATH`. `BOB_HOME` relativo → só `PATH`. | CT8 "U3 acrescenta", ADR 0019 |
| R12 | `bob doctor --install`: `install_npm_dependencies(lang)`; se ≠ 0, devolve esse código. Depois `ensure_gitleaks(bob_home())`; `GitleaksError` → 1 linha `bob doctor: <motivo>` no stderr e `4`. Depois o relatório de sempre. | CT8 |
| R13 | O harness não põe nenhum gitleaks no `PATH`; serve o tar.gz real (do cache conferido) em `<mirror>/gitleaks/<asset>` e uma cópia +1 byte em `<mirror>/gitleaks-bad/<asset>`; repassa `BOB_GITLEAKS_BASE_URL` no `env -i`. | pronto 2, CT15, CT18 passo 14 |

## Interface de `gitleaks.py` (CT9 + acréscimos compatíveis)
```python
VERSION = "8.30.1"
DEFAULT_BASE_URL = f"https://github.com/gitleaks/gitleaks/releases/download/v{VERSION}"
ASSETS: dict[tuple[str, str], tuple[str, str]]  # ("linux"|"darwin", "x64"|"arm64") -> (asset, sha256)
class GitleaksError(ToolError): ...
def platform_key(system: str | None = None, machine: str | None = None) -> tuple[str, str]: ...
def base_url(env: Mapping[str, str] = os.environ) -> str: ...            # acréscimo (R8)
def asset_url(key: tuple[str, str], base: str = DEFAULT_BASE_URL) -> str: ...  # acréscimo
def installed_version(home: BobHome) -> str | None: ...                  # acréscimo (R7)
def ensure_gitleaks(home: BobHome) -> Path: ...                          # devolve home.bin / "gitleaks"
```
Acréscimos compatíveis ao CT9 (nenhum nome do CT9 muda): `DEFAULT_BASE_URL`, `base_url`, `asset_url`, `installed_version`; mensagens extras `gitleaks.url_not_allowed` e `gitleaks.write` (o CT9 lista 4 erros; R6 e R8 precisam de 2 mais).

Mapeamento de plataforma (`platform_key`, CT9):
| `system` | `machine` | chave |
|---|---|---|
| `Linux` | `x86_64`, `amd64` | `("linux", "x64")` |
| `Linux` | `aarch64`, `arm64` | `("linux", "arm64")` |
| `Darwin` | `x86_64` | `("darwin", "x64")` |
| `Darwin` | `arm64` | `("darwin", "arm64")` |
| outro | outro | `GitleaksError` plataforma com `<so>/<arch>` = valores crus |

## Fluxo `ensure_gitleaks(home)`
| Ordem | Etapa | Escreve em | Falha |
|---|---|---|---|
| 1 | `installed_version(home) == VERSION` → devolve `home.bin / "gitleaks"` | nada | — |
| 2 | `key = platform_key()`; `asset, sha = ASSETS[key]` | nada | plataforma |
| 3 | `url = asset_url(key, base_url())` | nada | URL |
| 4 | `TemporaryDirectory(prefix="bob-gitleaks-")` no `TMPDIR`; download para `<tmp>/<asset>` (R9) | só `<tmp>` | download |
| 5 | `hashlib.sha256` do arquivo ≠ `sha` | só `<tmp>` | integridade |
| 6 | `tarfile` `r:gz`; membro único `gitleaks`, regular → bytes para `<tmp>/gitleaks` | só `<tmp>` | extração |
| 7 | `mkdir -p tools/gitleaks/8.30.1`; `gitleaks.tmp`; `chmod 0755`; `os.replace` | `tools/gitleaks/8.30.1/` | escrita (R6) |
| 8 | `mkdir -p bin`; `symlink("../tools/gitleaks/8.30.1/gitleaks", "bin/gitleaks.tmp")`; `os.replace` → `bin/gitleaks` | `bin/` | escrita (R6) |
| 9 | Apaga `<tmp>` (sempre, também em falha) | — | — |

## Mensagens (catálogo `messages.py`, en e pt-BR)
| Chave | en | pt-BR |
|---|---|---|
| `gitleaks.platform` | `gitleaks: {system}/{machine} is not in the table. Supported: linux x64/arm64, darwin x64/arm64.` | `gitleaks: {system}/{machine} não está na tabela. Suportadas: linux x64/arm64, darwin x64/arm64.` |
| `gitleaks.url_not_allowed` | `gitleaks: BOB_GITLEAKS_BASE_URL={value} is not allowed (https, or http only on 127.0.0.1/localhost). Fix the variable.` | `gitleaks: BOB_GITLEAKS_BASE_URL={value} não é permitida (https, ou http só em 127.0.0.1/localhost). Corrija a variável.` |
| `gitleaks.download` | `gitleaks: download of {url} failed ({status}). Check the network and try again.` | `gitleaks: download de {url} falhou ({status}). Confira a rede e tente de novo.` |
| `gitleaks.integrity` | `gitleaks: the sha256 of {asset} does not match. Nothing was installed. Try again.` | `gitleaks: o sha256 de {asset} não confere. Nada foi instalado. Tente de novo.` |
| `gitleaks.extract` | `gitleaks: {asset} does not have the expected gitleaks binary. Nothing was installed. Open an issue.` | `gitleaks: {asset} não tem o binário gitleaks esperado. Nada foi instalado. Abra uma issue.` |
| `gitleaks.write` | `gitleaks: could not write {path} ({detail}). Check the permissions.` | `gitleaks: não consegui gravar {path} ({detail}). Confira as permissões.` |
| `setup.item_gitleaks` | `gitleaks {version} in BOB_HOME/bin` | `gitleaks {version} em BOB_HOME/bin` |
| `doctor.bob_home_relative` | `BOB_HOME={value} must be absolute. Use an absolute path.` | `BOB_HOME={value} precisa ser absoluto. Use um caminho absoluto.` |

`{status}`: `HTTP <código>` para `urllib.error.HTTPError`; senão o nome da classe da causa (`exc.reason` de `URLError`, ou a própria exceção), p. ex. `ConnectionRefusedError`, `TimeoutError`. Na saída do `bob setup`: `bob setup: gitleaks: the sha256 of gitleaks_8.30.1_linux_x64.tar.gz does not match. Nothing was installed. Try again.` (cita `gitleaks` e `sha256`: passo 9 do Comando).

## Passo `gitleaks` no `bob setup` (CT3, ordem 4)
| Situação | `StepResult` |
|---|---|
| `installed_version(home) == VERSION` | `unchanged` (não chama `ensure_gitleaks`) |
| senão, `ensure_gitleaks` ok | `installed`, `installed=(msg("setup.item_gitleaks", version=VERSION),)` |
| `GitleaksError` | `failed`, `error = reason(exc)` (texto já começa com `gitleaks:`) |

`STEPS` = `projeto`, `runtimes`, `npm`, `gitleaks`, `skills`.

## Doctor (CT8, "U3 acrescenta")
- Pin do gitleaks derivado da tabela: `BinaryPin("gitleaks", gitleaks.VERSION, "gitleaks", gitleaks.asset_url(("linux", "x64")), gitleaks.ASSETS[("linux", "x64")][1])`. Mesmos valores de hoje (os workflows conferem esse par; `test_gitleaks_checksum_is_the_one_the_workflows_check` continua igual). A dica de instalação segue com o asset linux_x64 (comportamento atual; fora do escopo).
- `_locate(executable)` → `user_dirs.locate_binary(executable)`: `BOB_HOME/bin/<nome>` se `is_file()` e `os.access(X_OK)`; senão `shutil.which(<nome>)` (um argumento só: os testes trocam `shutil.which` por função de 1 parâmetro).
- `--install` conforme R12.

## Harness (CT15; passos 2 completo, 7 e 9a)
| Passo | Muda |
|---|---|
| todos | `tool_path` sem `$T/fixture-bin`. `run_oneliner` falha o passo se `PATH="$_path" command -v gitleaks` acha algo (`gitleaks já está no PATH (<caminho>); a máquina não está limpa.`) e repassa `BOB_GITLEAKS_BASE_URL=$GL_URL` quando `GL_URL` não é vazia. |
| preparo | Modo espelho: `prepare_gitleaks` mantém cache e conferência, e copia o tar.gz para `$T/mirror/gitleaks/<asset>` e `$T/mirror/gitleaks-bad/<asset>` (+ `\n`). `VERIFY_REMOTE=1`: não roda (o `bob setup` baixa do GitHub). |
| 2 | Pedidos ao espelho: os 4 de hoje + `GET /gitleaks/<asset> 200`, nesta ordem. `readlink BOB_HOME/bin/gitleaks` = `../tools/gitleaks/8.30.1/gitleaks`; `BOB_HOME/bin/gitleaks version` = `8.30.1`; modo do binário `755`. |
| 7 | 0 pedidos com `/gitleaks/` no espelho durante o passo (só modo espelho); `st_mtime_ns` de `tools/gitleaks/8.30.1/gitleaks` igual (os dois modos). |
| 9a (novo) | Release boa, `BOB_GITLEAKS_BASE_URL=$BASE/gitleaks-bad`, `HOME` novo: sai `4`; uma linha do stderr começa com `bob setup: gitleaks:` e contém `sha256`; `BOB_HOME/tools/gitleaks` e `BOB_HOME/bin/gitleaks` não existem; última linha do stdout `  bob doctor: not run`; exatamente 1 `GET /gitleaks-bad/<asset> 200`; projeto igual. `VERIFY_REMOTE=1` → não se aplica. |
| ids | `STEP_IDS='1 2 3 4 7 8 9a 9b'`. |

## Códigos de saída
| Situação | Saída |
|---|---|
| `bob setup` com qualquer `GitleaksError` | `4` (resumo parcial, `bob doctor: not run`) |
| `bob doctor --install` com `GitleaksError` | `4` |
| `bob doctor` com gitleaks ≠ 8.30.1 em `BOB_HOME/bin` e no `PATH` | `4` (como hoje) |
| Harness | `0` tudo ok; `1` no primeiro passo que falha |

## Fora do desenho
- Bloco 11 do prompt de IA e teste de paridade (U8). Matriz Linux/macOS × x64/arm64 (U9). `bob --version`/`bob update` (U7; o "`bob --version` = versão da release" do passo 2 é da U7).
- Dica de instalação do doctor por plataforma; texto `cli.setup` ("npm tools, skills"): ficam como estão.
- `install.sh` e `CURL_OPTS` (I15 resolvida com Q1 = A: só o texto do CT14 mudou).
