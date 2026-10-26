# U7 — u7-update-versao — Desenho funcional (3.1, Minimal)

Kind: library | Base: `main` @ `22d461a60920ab13e7b09fd654fd0e4686ba14d0` | Data: 2026-10-22 (UTC-3)
Contratos: CT11 (`bob update`, `bob --version`), CT8 (linha 3 do doctor), CT4 (acréscimo `manifest_skill_names`), CT12, CT14, CT15 (passos 2 parcial, 10 e 11). ADRs: 0018, 0011. Propostas: ADR 0024, 0025, 0026, 0027 (`../u6-u7-decisions-proposta.md`).
Perguntas: **Q1** (`functional-design-questions.md`): como mostrar skills em parte ausentes. A U7 T1 depende dela. O desenho abaixo usa a recomendação A, marcada "(Q1)".

## O que passa a existir
- `src/bob_quality/project_version.py`: estado das skills do bob no projeto.
- Linha `project skills:` / `skills do projeto:` no fim do `bob doctor`.
- `bob --version` (2 linhas) e `bob update`.
- Passos 10 e 11 do harness, e o passo 2 confere `bob --version`.

## Estado atual do repo (conferido @ 22d461a)
- `cli.py` (sem `update`, sem `--version`):
  - `build_parser` (57-127): `--lang` 62, `--config` oculto 63-68, `add_subparsers(required=True)` 69, `setup` 124-125;
  - `_Parser.exit` (28-33): status 0 vira `Help`;
  - `main` (211-231): `setup` em 223-224.
- `doctor.py`: `_report_pins` (156-163) imprime as linhas e devolve `_verdict(rows)`.
- `install_skills.py`: `default_source` (91-95), `_skill_entries` (150-157), `SourceError` (87). O manifesto lista `./skills/bob-check`, `./skills/harden` e `./skills/review-report`.
- `gitleaks.py`: rede com `urlopen`, 3 tentativas, pausa de 1,0 s, `_RETRYABLE` (59-64), `_client_error` (142), `_status` (151), `_ALLOWED_URL` (50).
- `install.sh`: `DEFAULT_API` (5), `DEFAULT_DOWNLOAD` (6), `BOB_VERSION` fixa a tag (348-351), `BOB_RELEASES_URL` (327-340).

## Regras — estado das skills do projeto (ADR 0024; T1)
| # | Regra |
|---|---|
| V1 | Nomes: os do manifesto empacotado (`install_skills.manifest_skill_names()`, o último componente de cada entrada). `SourceError` ou lista vazia → `not_installed`. |
| V2 | Por nome, `<projeto>/.agents/skills/<nome>/.bob-version` vale só se não é symlink, é arquivo regular e o conteúdo é exatamente `\d+\.\d+\.\d+\n` (bytes). Qualquer outra coisa (inclusive `OSError`) conta como ausente. |
| V3 | 0 válidas → `not_installed`. Todas válidas e iguais → `installed (<v>)`. Senão `mixed`, com as versões distintas em ordem numérica (tupla de inteiros) e `missing = True` se alguma faltou (Q1). |
| V4 | Texto: `installed` → `<v> (.agents/skills)`; `not_installed` → `not installed` / `não instaladas`; `mixed` → `mixed (<v1>, <v2>)` / `misturadas (…)`; `mixed` com falta → `mixed (<v…>, not installed)` / `misturadas (<v…>, não instaladas)` (Q1). |
| V5 | Linha: `project skills: <texto>` / `skills do projeto: <texto>`. No doctor, sai como última linha do stdout, com o `cwd`, só quando os pins foram lidos. Não muda o código de saída. |

## Regras — `bob --version` (ADR 0025; T2)
- Opção de topo. Imprime `bob <X.Y.Z>` (de `importlib.metadata.version("bob-quality")`) e a linha V5 do `cwd`, e sai `0`. Vale fora de repo git e sem subcomando.
- O idioma vem de `--lang`, `BOB_LANG` ou `bob.yaml` (`_language`).

## Regras — `bob update [--lang]` (CT11, ADR 0025; T2)
| # | Passo | Regra | Saída em erro |
|---|---|---|---|
| U1 | `projeto` | `BOB_HOME` relativo → `setup.bob_home_relative`. `setup_cmd.step_projeto` no `cwd` resolvido. | stderr `bob update: <motivo>`, `4` |
| U2 | `versão` | URLs: sem `BOB_RELEASES_URL` → `DEFAULT_API`/`DEFAULT_DOWNLOAD` (iguais aos do `install.sh`). Com ela: tira 1 `/` final, valida pela regex de `gitleaks._ALLOWED_URL` e usa `<base>/api/releases/latest` e `<base>/download`. `GET` na API com `Accept: application/vnd.github+json`, `timeout=30`; 3 tentativas com pausa de 1,0 s só em erro de rede, timeout ou `5xx`. `tag_name` precisa casar `v\d+\.\d+\.\d+`. | `versão: BOB_RELEASES_URL=<v> …`; `versão: could not read the latest release (<status>). Try again.`; `(invalid response)`. Todas `4` |
| U3 | `comparar` | `pacote` = tupla da versão do pacote (fora de `X.Y.Z` = mais velha). `projeto atual` = estado `installed` com versão ≥ última. Pacote ≥ última e projeto atual → `bob update: already on the newest release (<tag>).`, `0`, nada muda. Pacote ≥ última e projeto não atual → `bob update: updating the project to <tag>.` e devolve o código de `run_setup(projeto, lang)`. Pacote < última → `bob update: updating from v<old> to <tag>.` e segue. | — |
| U4 | `download` | `<dl>/<tag>/install.sh` e depois `<dl>/<tag>/SHA256SUMS`, sem `Accept`, mesmas tentativas, num `mkdtemp(prefix="bob-update.")` apagado no fim (sempre). `404` → release incompleta. Outro erro → download falhou. | `download: …`, `4` |
| U5 | `integridade` | `SHA256SUMS` em bytes: a 1ª linha cujo nome (o que vem depois do 1º `"  "`) é `install.sh`. O hash dela tem que ser igual ao `sha256` hex minúsculo do `install.sh` baixado. Sem linha ou diferente → falha. | `integridade: the sha256 of install.sh does not match. Nothing was installed. Try again.`, `4` |
| U6 | `instalar` | `subprocess.run(["sh", <script>, "--lang", <lang>], cwd=<projeto>, env={**os.environ, "BOB_VERSION": <tag>}, check=False)`. Devolve o código do filho. `OSError` → erro. | `instalar: could not run sh (<detalhe>).`, `4` |

Nunca altera `bob.yaml`, `.bob/waivers.yaml`, hook alheio nem skill alheia: quem escreve é o `install.sh` e o `bob setup` (CT3, CT4, CT7, CT10).

## Mensagens (catálogo; en / pt-BR)
| Chave | en | pt-BR |
|---|---|---|
| `version.skills` | `project skills: {state}` | `skills do projeto: {state}` |
| `version.at` | `{version} (.agents/skills)` | `{version} (.agents/skills)` |
| `version.not_installed` | `not installed` | `não instaladas` |
| `version.mixed` | `mixed ({versions})` | `misturadas ({versions})` |
| `version.mixed_missing` | `mixed ({versions}, not installed)` | `misturadas ({versions}, não instaladas)` |
| `version.bob` | `bob {version}` | `bob {version}` |
| `cli.update` | `Update bob and this project to the latest published release` | `Atualiza o bob e este projeto para a última release publicada` |
| `cli.version` | `Show the bob version and the project skills version` | `Mostra a versão do bob e a das skills do projeto` |
| `update.error` | `bob update: {reason}` | `bob update: {reason}` |
| `update.up_to_date` | `bob update: already on the newest release ({tag}).` | `bob update: já está na release mais nova ({tag}).` |
| `update.project_only` | `bob update: updating the project to {tag}.` | `bob update: atualizando o projeto para {tag}.` |
| `update.upgrading` | `bob update: updating from v{old} to {tag}.` | `bob update: atualizando de v{old} para {tag}.` |
| `update.api_failed` | `versão: could not read the latest release ({status}). Try again.` | `versão: não consegui ler a última release ({status}). Tente de novo.` |
| `update.bad_response` | `invalid response` | `resposta inválida` |
| `update.url_not_allowed` | `versão: BOB_RELEASES_URL={url} is not allowed. Use https://, or http:// only on 127.0.0.1 or localhost.` | `versão: BOB_RELEASES_URL={url} não é permitida. Use https://, ou http:// só em 127.0.0.1 ou localhost.` |
| `update.tmp_failed` | `download: could not create a temporary folder ({detail}).` | `download: não consegui criar uma pasta temporária ({detail}).` |
| `update.download_failed` | `download: {url} failed ({status}). Check the network and try again.` | `download: {url} falhou ({status}). Confira a rede e tente de novo.` |
| `update.download_missing` | `download: release {tag} is incomplete ({asset} missing). Open an issue.` | `download: a release {tag} está incompleta ({asset} ausente). Abra uma issue.` |
| `update.integrity` | `integridade: the sha256 of {file} does not match. Nothing was installed. Try again.` | `integridade: o sha256 de {file} não confere. Nada foi instalado. Tente de novo.` |
| `update.install_failed` | `instalar: could not run sh ({detail}).` | `instalar: não consegui rodar o sh ({detail}).` |

Os textos pt-BR de `update.api_failed`, `up_to_date`, `project_only` e `upgrading` são os do CT11. Os de `download`, `integridade` e `url_not_allowed` seguem os do `install.sh`. Os en são tradução.

## Harness (CT15; ADR 0026; T3)
- **Passo 2 (parcial):** só no modo espelho, `bob --version` no projeto do passo 2 = `bob $X` e `project skills: $X (.agents/skills)`.
- **Passo 10:**
  - Espelho `$T/mirror/upd/`:
    - `latest` = `v<X.Y.Z+1>`, com o wheel do build rebatizado;
    - `v$X` também publicada;
    - pré-release `v99.1.0` e rascunho `v99.1.1` fora do `latest`.
  - No projeto e `HOME` do passo 8, `bob update`:
    - sai `0`, com os pedidos exatos ao espelho;
    - `bob --version` mostra a nova nas 2 linhas;
    - `.bob-version` = nova em todas as skills;
    - `current` → `versions/<nova>`;
    - os itens preservados do passo 8 com hash igual;
    - `bob doctor: 0`.
  - O comando único num projeto novo, no mesmo `HOME`, instala a `latest` e não a pré-release (US7.2 crit. 1).
- **Passo 11:** `bob update` de novo sai `0`, com 1 linha "already on the newest release", 1 pedido (a API) e o `digest` do projeto igual.

## Fora do desenho
- Docs (U8).
- Release real (U9).
- Juntar a rede de `update.py` e `gitleaks.py` (fica para depois; o `dry` só reporta).
