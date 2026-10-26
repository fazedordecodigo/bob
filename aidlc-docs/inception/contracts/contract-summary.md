# 2.8 Contratos — bob (Minimal)

Autor: Arquiteto Técnico. Data: 2026-10-18 (UTC-3).
Insumos aprovados (só leitura): 2.7 (`inception/units/`), 2.6 (`inception/application-design/`), `requirements.md` (com RA1), `stories.md`.
Base do repo: `fazedordecodigo/bob` `main` @ `d2e26bd` (conferido em 2026-10-18 18:5x UTC-3; leitura remota, sem clone). Evidência no formato `arquivo:linha` desse commit.

## Regras de versionamento
- Todo contrato nasce `v1`.
- Mudança compatível (campo novo opcional, linha nova informativa, mensagem com texto melhor sem mudar chave nem código): mesma versão, com nota em "Registro".
- Mudança incompatível (remover ou renomear flag, variável, arquivo, chave, campo; mudar código de saída; mudar formato de linha que alguém lê por máquina; mudar nome de asset): **nova versão** (`v2`), mantendo a `v1` até a última consumidora migrar, e **aviso ao Maestro** antes da ET.
- Quem muda um contrato é a unit dona. Consumidora que precisa de mudança pede à dona pelo Maestro.
- Comportamento existente no repo que um contrato cita como "preservado" só muda com nova versão.

## Índice
| ID | Nome | Versão | Dona (produtora) | Consumidoras |
|---|---|---|---|---|
| CT1 | Saída, erros, idioma e códigos de saída | v1 | U1 | U3, U4, U5, U6, U7, U9 |
| CT2 | CLI `install.sh` | v1 | U1 | U6, U7, U8, U9 |
| CT3 | `bob setup`: CLI, registro de passos e resumo | v1 | U1 | U3, U4, U5, U6, U7, U8 |
| CT4 | Skills: `install_skills`, posse e `.bob-version` | v1 | U1 | U7, U8 |
| CT5 | Layout de instalação e marcadores | v1 | U1 | U3, U5, U6, U7, U8 |
| CT6 | Variáveis de ambiente | v2 | U1 | U3, U6, U7, U8, U9 |
| CT7 | `bob.yaml` gerado | v2 | U4 | U8, U9 |
| CT8 | `bob doctor` e fonte das versões npm | v1 | U2 | U1, U3, U7, U8, U9 |
| CT9 | gitleaks | v1 | U3 | U8, U9 |
| CT10 | Hook pre-push | v1 | U5 | U8, U9 |
| CT11 | `bob update` e `bob --version` | v1 | U7 | U8, U9 |
| CT12 | Formato de release | v1 | U1 | U7, U8, U9 |
| CT13 | Workflow `release.yml` e release-check | v1 | U9 | nenhuma unit (operação do Emerson, E1–E6) |
| CT14 | APIs externas | v1 | U1 (registro) | U3, U7, U8, U9 |
| CT15 | Harness `scripts/verify-install.sh` | v1.1 | U1 | U3, U4, U5, U6, U7, U8, U9 |
| CT16 | Perfil do shell (passo `perfil` do `install.sh`) | v2 | U6 | U8, U9 |
| CT17 | Docs de instalação e teste de paridade | v1 | U8 | U9 |
| CT18 | Prompt para agente de IA, sem `install.sh` (alternativa ao CT2) | v1 | U8 | U9 |

Regra de direção: toda consumidora depende da dona no DAG (`unit-of-work-dependency.md`). Conferido por script em `contract-traceability.md`.

---

## CT1 — Saída, erros, idioma e códigos de saída (v1)
**Preservado do repo.**
- Códigos: `0` PASSED, `1` GATE_FAILED, `2` BASELINE_BROKEN, `3` UNWAIVED_SURVIVOR, `4` CONFIG_OR_TOOL (`src/bob_quality/exit_codes.py:3-7`; `docs/exit-codes.md:7-13`). Uso inválido da CLI sai `4` (`docs/exit-codes.md:13`; `cli.py` `_stop_code`).
- Idiomas: `en` (padrão) e `pt-BR` (`messages.py:8-10`). Ordem: `--lang`, depois `BOB_LANG`, depois `language` do `bob.yaml`, depois `en` (`config.py:333-345`). Valor fora da lista: `ConfigError` → `4` (`config.py:361-366`).
- Mensagens novas do pacote Python entram no catálogo `messages.py` (`_EN` e `_PT_BR`), com chave. Nada de texto solto.

**Novo.**
- Comandos novos (`bob setup`, `bob update`, `bob --version`) e `install.sh` usam só `0` e `4`. Exceção: `bob setup` e `install.sh` repassam o código do `bob doctor` (`0` ou `4`). `scripts/verify-install.sh` usa `0`/`1` (CT15).
- Formato padrão de erro, sempre no **stderr**, uma linha:
  `<prefixo>: <passo>: <o que falhou>. <ação>.`
  - `<prefixo>` ∈ {`install`, `bob setup`, `bob update`, `bob doctor`}.
  - `<passo>`: id do passo, minúsculo, sem espaço (tabelas de CT2 e CT3).
- Aviso (não falha): stdout, `<prefixo>: <passo>: aviso: <texto>.` (en: `warning:`).
- Gate `not_run` contribui `0` quando não há o que medir: gate desconhecido (`check.gate_not_implemented`), `dry` sem ferramenta e, desde a T1b, `crap` e `coverage` sem código no `paths.include` (`check.no_code`). `not_run` por ferramenta ausente ou quebrada num projeto com código segue `4`.
  - Emenda E3 (T1b), aprovada pelo Emerson em 2026-10-20 21:42 UTC-3 ("Aprovo a T1b e as emendas E1 a E3, com a T1c separada para a E4."); origem: Q1 = A e `construction/u4-bob-yaml/code-generation/tasks/T1b-emenda.md`.
- Linha de progresso: stdout, `<prefixo>: <passo>: <texto curto>`.
- Toda falha de CT2/CT3/CT11 é uma linha nesse formato (NFR9, 100%).

## CT2 — CLI `install.sh` (v1)
**Sintaxe.**
```sh
curl -fsSL https://github.com/fazedordecodigo/bob/releases/latest/download/install.sh | sh
curl -fsSL https://github.com/fazedordecodigo/bob/releases/latest/download/install.sh | sh -s -- --lang pt-BR
sh install.sh [--lang en|pt-BR] [--help]
```
- Shell POSIX `/bin/sh`. Sem bashismos (o 3.6 roda `sh -n` e `dash` no Linux).
- Args: `--lang <en|pt-BR>`; `--help` (imprime uso, sai `0`). Qualquer outro: `install: uso: argumento desconhecido <arg>. Rode com --help.` e `4`.
- Idioma: `--lang`, senão `BOB_LANG`, senão `en`. Valor inválido: erro de uso, `4`.
- Env lidas: CT6 (`BOB_VERSION`, `BOB_RELEASES_URL`, `BOB_HOME`, `XDG_DATA_HOME`, `BOB_LANG`, `HOME`, `PATH`, `SHELL`, `ZDOTDIR`).
- Ferramentas exigidas: `uname`, `curl`, `python3`, `node`, `npm`, `git`, e `sha256sum` ou `shasum`.

**Passos (ordem fixa; para no primeiro que falha).**
| Id | Confere / faz | Erro (pt-BR; en tem o mesmo conteúdo) | Saída |
|---|---|---|---|
| `projeto` | `git` existe e `git rev-parse --show-toplevel` = `pwd -P` | `install: projeto: <dir> não é a raiz de um repositório git. Rode na raiz do projeto.` | 4 |
| `plataforma` | `uname -s` ∈ {Linux, Darwin}; `uname -m` ∈ {x86_64, amd64, aarch64, arm64} | `install: plataforma: <so>/<arch> não é suportada. Suportadas: Linux e macOS, x64 e arm64.` | 4 |
| `python` | `python3` ≥ 3.10 (`sys.version_info`); `python3 -c 'import venv, ensurepip'` | `install: python: encontrado <v>, exigido >=3.10. Instale um Python 3.10 ou mais novo.` / `install: python: o módulo venv não está disponível. No Ubuntu, instale o pacote python3-venv.` | 4 |
| `node` | `node --version` = `vX.Y.Z` sem sufixo, `22.18.0 ≤ v < 23`; `npm --version` existe | `install: node: encontrado <v>, exigido >=22.18.0 <23. Instale o Node 22.18.0 ou mais novo da linha 22.` | 4 |
| `ferramentas` | `curl`; `sha256sum` ou `shasum` | `install: ferramentas: <nome> não encontrado. Instale <nome> e rode de novo.` | 4 |
| `versão` | API `releases/latest` (CT14) → `tag_name` (padrão, sempre); `BOB_VERSION` (CT6) só em testes, release-check e `bob update` | `install: versão: não consegui ler a última release (<status>). Tente de novo mais tarde.` | 4 |
| `download` | wheel e `SHA256SUMS` da tag (CT12) para temporário | `install: download: <url> falhou (<status>). Confira a rede e tente de novo.` | 4 |
| `integridade` | sha256 do wheel = linha dele no `SHA256SUMS` | `install: integridade: o sha256 de <arquivo> não confere. Nada foi instalado. Tente de novo.` | 4 |
| `pacote` | venv em `versions/<v>/venv`, `pip install --disable-pip-version-check --no-input <wheel>`, marca `.complete` (CT5) | `install: pacote: pip falhou. Veja a saída acima e tente de novo.` | 4 |
| `launcher` | troca `current` e liga `bin/bob` e `~/.local/bin/bob` (CT5) | `install: launcher: não consegui criar <caminho> (<erro>). Confira as permissões.` | 4 |
| `perfil` | U6, contrato CT16; nunca falha | aviso (CT16) | — |
| `setup` | `export BOB_INSTALL_PROFILE=<r>` e `exec "$BOB_HOME/bin/bob" setup --lang <l> </dev/null` (CT3; ADR 0022) | (do `bob setup`) | código do `bob setup` |

- Os passos `projeto` a `ferramentas` não escrevem nada em lugar nenhum (US1.2 crit. 3). Até `launcher`, 0 arquivos do projeto mudam.
- Venv já existe com `.complete` igual ao sha256 do wheel: reusa, não reinstala.
- Falha em `pacote`: apaga `versions/<v>` incompleto. `current` não muda.
- Progresso no stdout: `install: <passo>: ok` (en e pt-BR iguais), e `install: versão: v<X.Y.Z>`.
- Rede: `curl -fsSL --connect-timeout 15 --max-time 300 --retry 2`. Detalhe em CT14.
- `BOB_VERSION` (esclarecimento compatível da v1, 2026-10-18 19:43 UTC-3): o uso normal é sempre a última release publicada (FR1.4). `BOB_VERSION` existe só para o harness/espelho (CT15), o release-check da pré-release (Q1 A do 2.7, E3 do U9) e o `bob update`, que passa ao filho a tag que ele mesmo leu de `releases/latest` (CT11). `--help` e mensagens de erro não a oferecem ao dev.
- Fontes únicas no topo do script, uma linha cada (lidas pelo teste de paridade do CT18): `STEPS`, `PROFILE_LINE`, `DEFAULT_API`, `DEFAULT_DOWNLOAD`, `CURL_OPTS`, `PIP_OPTS` (valores exatos no CT18). O script usa essas variáveis; não repete os literais.

## CT3 — `bob setup`: CLI, registro de passos e resumo (v1)
**CLI.**
```
bob setup [--lang en|pt-BR]
```
- Sem `--config`, sem outros flags (como `doctor`, `cli.py:115-121`). Projeto = `cwd`.
- Não pergunta nada. Idempotente.
- Saída: `0` se todos os passos passam e o doctor sai `0`; `4` se o doctor sai `4` ou um passo falha.
- Lê `BOB_INSTALL_PROFILE` (CT6) só para a linha do resumo.

**Registro de passos (interface Python, dona U1; `src/bob_quality/setup_cmd.py`).**
```python
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal
from bob_quality.messages import Language, Text
from bob_quality.user_dirs import BobHome

Status = Literal["installed", "unchanged", "preserved", "failed"]

@dataclass(frozen=True)
class SetupContext:
    project: Path        # raiz git, absoluta
    home: BobHome        # CT5
    lang: Language
    version: str         # versão do pacote, "X.Y.Z"

@dataclass(frozen=True)
class StepResult:
    status: Status
    installed: tuple[Text, ...] = ()       # itens para "instalado"
    preserved: tuple[Text, ...] = ()       # "<item> (<motivo>)"
    warnings: tuple[Text, ...] = ()
    error: Text | None = None              # obrigatório se status == "failed"; linha CT1 sem o prefixo

Step = Callable[[SetupContext], StepResult]
STEPS: tuple[tuple[str, Step], ...]       # ordem abaixo
```
- Um passo **não** imprime nada nem chama `sys.exit`. Exceção não tratada num passo é bug: vira `failed` com `error = "<passo>: erro interno (<tipo>). Abra uma issue."`.
- O `bob setup` para no primeiro `failed`, imprime o erro (CT1) e o resumo parcial, sai `4`.

| Ordem | Id | Dona do passo | Faz |
|---|---|---|---|
| 1 | `projeto` | U1 | raiz git = `cwd` |
| 2 | `runtimes` | U1 | Python ≥ 3.10; Node em `node_range()` (CT8) |
| 3 | `npm` | U1 | `install_npm_dependencies()` (existente, `npm_tools.py:133-142`) |
| 4 | `gitleaks` | U3 | `ensure_gitleaks(home)` (CT9) |
| 5 | `skills` | U1 | `install_project_skills(project, version)` (CT4) |
| 6 | `bob.yaml` | U4 | `write_default_config(project)` (CT7) |
| 7 | `hook` | U5 | `install_hook(project, home.bin_bob)` (CT10) |
| 8 | `doctor` | U1 | `run_doctor(install=False, lang)` (CT8); código vira o código final |

Units U3, U4, U5 entram só inserindo a tupla na posição da tabela. Antes de existirem, o passo não aparece.

**Resumo (stdout, depois do último passo).**
```
bob setup: resumo
  instalado: <item>, <item>, ...
  preservado: <item> (<motivo>)
  avisos: <texto>
  perfil do shell: <texto>
  bob doctor: <0|4>
```
- en: `bob setup: summary`, `installed:`, `preserved:`, `warnings:`, `shell profile:`, `bob doctor:`.
- `instalado` e `bob doctor` sempre aparecem (`instalado: nada` / `installed: nothing` quando vazio).
- `preservado` e `avisos`: uma linha por item; omitidas se vazias.
- `perfil do shell`: só se `BOB_INSTALL_PROFILE` existe (também no resumo parcial). Textos (pt-BR; ADR 0013 / ADR 0023):
  - `<arquivo absoluto>` → `acrescentei ~/.local/bin ao PATH em <arquivo>. Abra um terminal novo ou rode: . <arquivo>` (en: `added ~/.local/bin to PATH in <arquivo>. Open a new terminal or run: . <arquivo>`)
  - `already-on-path` → `~/.local/bin já está no PATH; nada mudou` (en: `~/.local/bin is already on PATH; nothing changed`)
  - `already-marked:<arquivo absoluto>` → `<arquivo> já tem a linha do bob; nada mudou` (en: `<arquivo> already has the bob line; nothing changed`)
  - `failed:<arquivo absoluto>` → `não consegui gravar <arquivo>; veja o aviso acima` (en: `could not write <arquivo>; see the warning above`)
  - caminho relativo, vazio ou outro valor → sem linha
- A última linha é sempre `  bob doctor: <código>` (o passo 2 do Comando de Verificação lê essa linha).

## CT4 — Skills: `install_skills`, posse e `.bob-version` (v1)
**CLI existente, preservada** (`install_skills.py:83-110`):
```
python -m bob_quality.install_skills [--project DIR] [--source DIR] {agents,copilot,devin}...
```
- stdout por pasta de destino: `<N> skills em <pasta>` (`install_skills.py:100`). Avisos no stderr: `aviso: <caminho> ficou, porque <motivo>.` Mensagens fixas em pt-BR, como hoje (o script roda sem o pacote; `install_skills.py:1-5`).
- Saída: `0`; fonte inválida `4` (`CONFIG_ERROR = 4`, `install_skills.py:76`).
- Muda (v1): `--source` padrão = `parents[2]` se tiver `.claude-plugin/plugin.json`; senão `bob_quality/plugin/` dentro do pacote (ADR 0010).

**Função nova (usada pelo `bob setup`).**
```python
def manifest_skill_names(source: Path | None = None) -> tuple[str, ...]:
    """Nomes das skills do manifesto (último componente de cada entrada).
    SourceError se o manifesto é inválido."""

def install_project_skills(project: Path, version: str) -> SkillsResult: ...

@dataclass(frozen=True)
class SkillsResult:
    installed: tuple[str, ...]        # nomes gravados ou atualizados
    unchanged: tuple[str, ...]
    preserved: tuple[Path, ...]       # pastas alheias mantidas
    duplicates: tuple[Path, ...]      # cópias do bob em .claude/skills ou .github/skills
```
- Destino único: `<project>/.agents/skills/<nome>/` (ADR 0009).
- Conteúdo de cada pasta: arquivos da skill no pacote + `LICENSE` + `.bob-version`.
- `.bob-version`: texto `X.Y.Z\n` (versão do pacote, sem `v`, uma linha, LF). É o marcador de posse.
- Regras:
  1. Pasta não existe → cria.
  2. Pasta com `.bob-version` → reescreve só se algum arquivo difere (compara bytes). Igual → `unchanged`, 0 escritas.
  3. Pasta sem `.bob-version` (inclui instalação antiga do bob) → não toca; `preserved`; aviso `skills: aviso: <pasta> não tem .bob-version e ficou como está. Se ela é do bob, apague a pasta e rode bob setup de novo.` (ver Inconsistência I2).
  4. Pasta com `.bob-version` cujo nome saiu do manifesto → apaga (skill aposentada).
  5. Caminho é symlink ou arquivo → não toca; `preserved` (como hoje, `install_skills.py:189-194`).
  6. Cópia com `.bob-version` em `.claude/skills/<nome>` ou `.github/skills/<nome>` → `duplicates`; aviso de CT3 (`component-interfaces.md` §2). Não apaga.
- Erro de escrita → `OSError` vira `failed` no passo `skills`: `skills: não consegui gravar <caminho> (<erro>). Confira as permissões.`

## CT5 — Layout de instalação e marcadores (v1)
```
$BOB_HOME/                                  # CT6
├── versions/<X.Y.Z>/venv/                  # venv da versão (python3 -m venv)
├── versions/<X.Y.Z>/.complete              # sha256 do wheel instalado + "\n"; escrito por último
├── current -> versions/<X.Y.Z>             # symlink relativo
├── bin/bob -> ../current/venv/bin/bob      # symlink relativo; caminho estável
├── bin/gitleaks -> ../tools/gitleaks/8.30.1/gitleaks   # U3
└── tools/gitleaks/8.30.1/gitleaks          # 0755, U3
~/.local/bin/bob -> $BOB_HOME/bin/bob       # symlink absoluto
```
- Troca de `current`: cria `current.tmp` (symlink) e faz `rename(2)` sobre `current` com `os.replace` do Python do venv novo (atômico; `mv` não é usado porque o BSD `mv` entra no diretório do link).
- `~/.local/bin/bob` existe e não é symlink para `$BOB_HOME/bin/bob` → não toca; aviso `install: launcher: aviso: <caminho> já existe e não é do bob; ficou como está.`
- Interface Python (dona U1, `src/bob_quality/user_dirs.py`):
  ```python
  @dataclass(frozen=True)
  class BobHome:
      root: Path            # absoluto
      versions: Path        # root / "versions"
      current: Path         # root / "current"
      bin: Path             # root / "bin"
      bin_bob: Path         # root / "bin" / "bob"
      tools: Path           # root / "tools"
  def bob_home(env: Mapping[str, str] = os.environ) -> BobHome: ...   # ValueError se BOB_HOME relativo
  ```
- Teste de paridade (U1): `install.sh` e `bob_home()` calculam o mesmo `root` para os mesmos env.
- Cache npm existente, preservado: `${XDG_CACHE_HOME:-~/.cache}/bob-quality` (`npm_tools.py:196-199`), usado só quando o pacote não aceita escrita.

**Marcadores.**
| Onde | Marcador exato | Dona |
|---|---|---|
| `.agents/skills/<nome>/.bob-version` | arquivo; conteúdo `X.Y.Z\n` | U1 |
| hook `pre-push` | linha 2 exata: `# managed-by: bob-quality` | U5 |
| perfil do shell | linha inteira: `export PATH="$HOME/.local/bin:$PATH" # managed-by: bob-quality` | U6 |
| `bob.yaml` | nenhum; existir = do dev (preserva) | U4 |

## CT6 — Variáveis de ambiente (v2)
| Nome | Tipo / valores | Padrão | Validação | Escreve | Lê |
|---|---|---|---|---|---|
| `BOB_VERSION` | tag `vX.Y.Z` | vazia → última release publicada | `^v[0-9]+\.[0-9]+\.[0-9]+$`; fora → `install: versão: BOB_VERSION=<v> inválida. Use vX.Y.Z.` e `4` | harness/espelho (CT15); Emerson no release-check da pré-release (E3 do U9); `bob update` (para o filho, com a tag lida de `releases/latest`). **Não é opção de uso normal do dev**: docs e mensagens não a oferecem, exceto numa nota marcada "somente testes/release-check" (esclarecimento compatível da v1) | `install.sh`; bloco `versão` do prompt (CT18) |
| `BOB_RELEASES_URL` | URL base | vazia → GitHub (CT12) | `https://…`, ou `http://` só com host `127.0.0.1` ou `localhost`; barra final removida; fora → `4` | harness (CT15); dev (espelho) | `install.sh`, `bob update` |
| `BOB_HOME` | caminho absoluto | `${XDG_DATA_HOME:-$HOME/.local/share}/bob-quality` | relativo → `install: launcher: BOB_HOME=<v> precisa ser absoluto.` e `4` | dev; harness | `install.sh`, `user_dirs.py` |
| `XDG_DATA_HOME` | caminho absoluto | `$HOME/.local/share` | relativo → ignorado (regra do XDG Base Directory: caminho relativo "should be considered invalid and ignored", https://specifications.freedesktop.org/basedir-spec/latest/, acessada 2026-10-18) | SO/dev | idem |
| `BOB_LANG` | `en`, `pt-BR` | `en` | existente (`config.py:337`); inválido → `4` | dev | todos |
| `BOB_INSTALL_PROFILE` | `<arquivo absoluto>`, `already-on-path`, `already-marked:<arquivo absoluto>`, `failed:<arquivo absoluto>` | ausente → sem linha | `<arquivo>`, `already-marked:` e `failed:` exigem caminho que começa com `/`; `already-marked` sem arquivo e qualquer outro valor → ignorado (sem linha). Interna, não documentada ao dev | `install.sh` (U6) | `bob setup` (U1) |
| `BOB_GITLEAKS_BASE_URL` | URL base | `https://github.com/gitleaks/gitleaks/releases/download/v8.30.1` | mesma regra de esquema de `BOB_RELEASES_URL` | harness | `gitleaks.py` (U3) |
| `VERIFY_REMOTE` | `1` | vazio → modo espelho local | só `1` liga | CI / Emerson | `verify-install.sh` |
| `SHELL`, `ZDOTDIR`, `HOME`, `PATH` | do SO | — | `SHELL` vazio → `~/.profile` (ADR 0013) | SO | `install.sh` (perfil, launcher) |
| `XDG_CACHE_HOME` | existente | `~/.cache` | existente (`npm_tools.py:197`) | SO | `npm_tools` |
| `BOB_VITEST_SETUP`, `BOB_USER_VITEST_CONFIG` | existentes, internas | — | sem mudança (`npm_tools.py:357-360`) | `npm_tools` | runner vitest |
| `PIP_*`, `npm_config_*` | do pip e do npm | — | repassadas sem mudança | dev | pip, npm |

## CT7 — `bob.yaml` gerado (v2)
**Preservado do repo.** Esquema em `config.py:90-271` (não há JSON Schema do `bob.yaml` no repo; `src/bob_quality/schemas/` só tem `report_v1.json`). Chave desconhecida → `4` (`config.py:470-473`). `paths.include` com pasta inexistente → `4` (`config.py:428-434`). Padrões em `config.py:275-297` e `README.pt-BR.md:182-203`. `DEFAULT_EXCLUDE = ["tests", "node_modules", "dist"]` (`config.py:15`).

**Função (dona U4, `src/bob_quality/init_config.py`).**
```python
ConfigState = Literal["created", "preserved", "created_no_code"]
@dataclass(frozen=True)
class ConfigResult:
    state: ConfigState
    include: tuple[str, ...]          # vazio se preserved
def write_default_config(project: Path) -> ConfigResult: ...   # ConfigError se o gerado não valida
```

**Texto gerado (exato; só `<INCLUDE>` varia).**
```yaml
base: origin/main
language: en
paths:
  include: <INCLUDE>
  exclude: [tests, node_modules, dist]
crap:
  max_per_function: 10
  scope: changed
duplication:
  min_tokens: 50
  new_clones: warn
  max_new_clones: 0
  min_similarity: 0
  min_lines: 0
coverage:
  min_percent: 80
dependencies:
  python: .importlinter
  typescript: .dependency-cruiser.cjs
```
- `<INCLUDE>`: lista YAML em fluxo. Itens sem aspas, exceto `"."`. Ex.: `[src]`, `[app, lib]`, `["."]`.
- Sem `languages` (detectada; `README.pt-BR.md:180`). Encoding UTF-8, LF, termina em `\n`.

**Regra de `paths.include` (ADR 0015, exata).**
1. Candidatos: `git ls-files -z --cached --others --exclude-standard`, rodado na raiz.
2. Mantém os de sufixo `.py .ts .tsx .js .jsx .mjs .cjs` que não são symlink.
3. Descarta os que casam com `DEFAULT_EXCLUDE` por `_excluded` (`config.py:417-425`).
4. Pasta candidata = 1º componente do caminho, se o arquivo não está na raiz e o componente não começa com `.`.
5. `src` entre as candidatas → `[src]`. Senão, candidatas → todas, `sorted()` (ordem de código Unicode). Senão, código na raiz → `["."]` (`created`). Senão → `["."]` (`created_no_code`, aviso `bob.yaml: aviso: nenhuma pasta de código encontrada; paths.include: ["."].`).
6. Grava em `bob.yaml.tmp-<pid>` no projeto, `load_config(tmp, project)`, `os.replace` para `bob.yaml`. `ConfigError` → apaga o temporário e propaga.
- `bob.yaml` existe (arquivo, symlink ou diretório) → `preserved`, 0 leituras para alterar, 0 escritas.

**Esquema do que é gerado** (subconjunto do esquema aceito por `config.py`; JSON Schema 2020-12, só para teste do 3.6):
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["base", "language", "paths", "crap", "duplication", "coverage", "dependencies"],
  "properties": {
    "base": {"const": "origin/main"},
    "language": {"const": "en"},
    "paths": {"type": "object", "additionalProperties": false, "required": ["include", "exclude"],
      "properties": {
        "include": {"type": "array", "minItems": 1, "items": {"type": "string", "minLength": 1}},
        "exclude": {"const": ["tests", "node_modules", "dist"]}}},
    "crap": {"const": {"max_per_function": 10, "scope": "changed"}},
    "duplication": {"const": {"min_tokens": 50, "new_clones": "warn", "max_new_clones": 0, "min_similarity": 0, "min_lines": 0}},
    "coverage": {"const": {"min_percent": 80}},
    "dependencies": {"const": {"python": ".importlinter", "typescript": ".dependency-cruiser.cjs"}}
  }
}
```
- Compatível: todo documento válido aqui é aceito por `load_config` (todas as chaves existem em `config.py:90-271`, valores dentro dos limites). O teste do U4 confere isso.

**`bob check`: o que muda.** Nada na CLI nem nos códigos. Só passa a achar um `bob.yaml` que não sai `4` por configuração (FR4.4). Nos gates, uma mudança (T1b, Q1 = A): quando `detect_languages(cwd, paths.include, paths.exclude)` é vazio, `crap` e `coverage` não rodam ferramenta, ficam `not_run` com o motivo `check.no_code` (en "no code to measure", pt-BR "nenhum código a medir") e contribuem `0`. Com código, tudo segue igual.

_Emenda E2 (T1b), aprovada pelo Emerson em 2026-10-20 21:42 UTC-3 ("Aprovo a T1b e as emendas E1 a E3, com a T1c separada para a E4."); origem: Q1 = A e `construction/u4-bob-yaml/code-generation/tasks/T1b-emenda.md`._

## CT8 — `bob doctor` e fonte das versões npm (v1)
**CLI, preservada:** `bob doctor [--install] [--lang en|pt-BR]` (`cli.py:115-121`). Sem `--config`.

**Saída, preservada** (stdout; `doctor.py:136-139`, `:167-172`):
1. Uma linha por pin, na ordem de `PINS` (`doctor.py:64-112`): en `<nome> expected <esperado> found <encontrado>`; pt-BR `<nome> esperada <esperado> encontrada <encontrado>` (`messages.py:209`, `:531`). Ausente: `missing` / `ausente`.
2. Depois, as linhas de instalação (pip, Node, gitleaks, dica `npm ci`), como hoje (`doctor.py:188-212`).
3. **Novo (U7, informativa, última linha):** en `project skills: <versão> (.agents/skills)` | `project skills: not installed` | `project skills: mixed (<v1>, <v2>)` | `project skills: mixed (<v…>, not installed)` quando uma parte falta (Q1 = A); pt-BR `skills do projeto: …` | `não instaladas` | `misturadas (…)` | `misturadas (<v…>, não instaladas)`. Versões em ordem numérica. Não muda o código.
- Código: `0` se todo pin bate; senão `4` (`doctor.py:175-178`). Sem mudança.

**Muda (U2, P1 e ADR 0019).**
- `NpmPin` perde `expected`; o esperado vem de `pinned_npm_versions()[npm_package]`.
- `NODE` vem de `node_range()`.
- Busca npm só no prefixo do bob; sai `Path.cwd()/node_modules` (`doctor.py:358-360`) e o `node_modules/.bin` do cwd em `_locate` (`doctor.py:437-441`).
- U3 acrescenta: binários procurados primeiro em `BOB_HOME/bin`, depois `PATH`; `--install` roda `install_npm_dependencies()` e depois `ensure_gitleaks()`; primeiro código ≠ 0 vence.
- Linha do gitleaks continua `gitleaks expected 8.30.1 found <v>`; a versão sai de `gitleaks --version` (`gitleaks version 8.30.1`, conferido no binário oficial em 2026-10-18).
- Erro de leitura do `package.json`: stderr `bob doctor: package.json: não consegui ler <caminho> (<erro>). Reinstale o bob.` e `4`.

**Interface Python (dona U2, `src/bob_quality/npm_tools.py`).**
```python
class PinSourceError(ToolError): ...      # ToolError: bob_quality.tools (importado em doctor.py:18)

def pinned_npm_versions() -> dict[str, str]:
    """`dependencies` do package.json empacotado: {nome npm: "X.Y.Z"}.
    PinSourceError se o arquivo falta, não é JSON, ou algum valor não casa ^\d+\.\d+\.\d+$."""

@dataclass(frozen=True)
class NodeRange:
    floor: tuple[int, int, int]           # (22, 18, 0)
    below_major: int                      # 23
    def __str__(self) -> str: ...         # ">=22.18.0 <23"

def node_range() -> NodeRange:
    """`engines.node` do package.json empacotado. Aceita só ">=A.B.C <N" com N == A + 1.
    PinSourceError fora disso."""
```
- Hoje: `package.json:5-7` tem `"node": ">=22.18.0 <23"`; `package.json:8-18` tem 9 deps exatas, vitest `5.0.5` (`:15`).
- `doctor.node_range(pin: NodePin) -> str` (`doctor.py:250-251`) **fica** (ver I1). `NODE = NodePin(floor=NodeVersion(*node_range().floor))`.
- Testes: `tests/test_npm_pin.py` deixa de ter a cópia fixa (`:21-31`) e confere `package-lock.json` = `package.json`; teste novo: `install.sh` tem a mesma faixa de Node e o mesmo piso de Python de `pyproject.toml:10`.

## CT9 — gitleaks (v1)
**Fonte:** release oficial v8.30.1 (https://github.com/gitleaks/gitleaks/releases/tag/v8.30.1). Valores = `gitleaks_8.30.1_checksums.txt` da mesma release = `digest` da API (ADR 0014). Em 2026-10-18 os 4 tar.gz foram baixados no box: `sha256sum` bate e cada um tem só `LICENSE`, `README.md` e `gitleaks` na raiz.

| `platform.system()` | `platform.machine()` | Asset | sha256 |
|---|---|---|---|
| `Linux` | `x86_64`, `amd64` | `gitleaks_8.30.1_linux_x64.tar.gz` | `551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb` |
| `Linux` | `aarch64`, `arm64` | `gitleaks_8.30.1_linux_arm64.tar.gz` | `e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080` |
| `Darwin` | `x86_64` | `gitleaks_8.30.1_darwin_x64.tar.gz` | `dfe101a4db2255fc85120ac7f3d25e4342c3c20cf749f2c20a18081af1952709` |
| `Darwin` | `arm64` | `gitleaks_8.30.1_darwin_arm64.tar.gz` | `b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5` |

- URL: `${BOB_GITLEAKS_BASE_URL}/<asset>`; padrão `https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/<asset>`.
- Interface (dona U3, `src/bob_quality/gitleaks.py`):
  ```python
  VERSION = "8.30.1"
  ASSETS: dict[tuple[str, str], tuple[str, str]]   # (system, arch) -> (asset, sha256); arch ∈ {"x64","arm64"}
  class GitleaksError(ToolError): ...               # passo, falha, ação
  def platform_key(system: str | None = None, machine: str | None = None) -> tuple[str, str]: ...  # GitleaksError fora da tabela
  def ensure_gitleaks(home: BobHome) -> Path: ...  # caminho de home.bin/"gitleaks"
  ```
- Fluxo: já existe `home.bin/gitleaks` com `--version` contendo `8.30.1` → devolve, 0 downloads. Senão: baixa para temp (timeout CT14) → sha256 → abre o tar e aceita só o membro `gitleaks` regular (sem `/`, sem `..`, sem link) → grava `tools/gitleaks/8.30.1/gitleaks.tmp`, `chmod 0755`, `os.replace` → link `bin/gitleaks` (troca por `os.replace`).
- Erros (todos `GitleaksError` → passo `gitleaks` `failed` → `4`; nada fica em `tools/gitleaks`):
  - plataforma: `gitleaks: <so>/<arch> não está na tabela. Suportadas: linux x64/arm64, darwin x64/arm64.`
  - download: `gitleaks: download de <url> falhou (<status>). Confira a rede e tente de novo.`
  - integridade: `gitleaks: o sha256 de <asset> não confere. Nada foi instalado. Tente de novo.`
  - extração: `gitleaks: <asset> não tem o binário gitleaks esperado. Nada foi instalado. Abra uma issue.`

## CT10 — Hook pre-push (v1)
**Preservado do repo:** comando `bob check --gates crap,dry,deps`, `set -e`, `unset PYTEST_ADDOPTS`, `unset PYTEST_PLUGINS`, `</dev/null` (`src/bob_quality/hooks/pre-push:1-5`).

**Template (exato; `<BOB_BIN>` = `home.bin_bob`, absoluto, sem aspas internas):**
```sh
#!/bin/sh
# managed-by: bob-quality
set -e
unset PYTEST_ADDOPTS
unset PYTEST_PLUGINS
BOB="<BOB_BIN>"
[ -x "$BOB" ] || BOB=bob
exec "$BOB" check --gates crap,dry,deps </dev/null
```
- Arquivo: `$(git rev-parse --git-path hooks)/pre-push`, modo `0755`, LF.
- Interface (dona U5, `src/bob_quality/hook_install.py`):
  ```python
  HookState = Literal["created", "updated", "unchanged", "preserved", "preserved_hookspath"]
  @dataclass(frozen=True)
  class HookResult:
      state: HookState
      path: Path
  def install_hook(project: Path, bob_bin: Path) -> HookResult: ...
  ```
- `core.hooksPath` definido → `preserved_hookspath`, nada gravado; aviso `hook: aviso: core.hooksPath=<valor>; hook não instalado. Acrescente ao seu gerenciador de hooks: <BOB_BIN> check --gates crap,dry,deps.`
- Existe sem a linha 2 exata → `preserved`; aviso `hook: aviso: hook pre-push existente preservado (<caminho>). Para usar o do bob, acrescente: <BOB_BIN> check --gates crap,dry,deps.`
- Existe com a linha → reescreve só se o conteúdo difere (`updated`), senão `unchanged`.
- Código de saída do hook = o do `bob check` (CT1). O git aborta o push quando o hook sai ≠ 0 (githooks, seção pre-push: https://git-scm.com/docs/githooks#_pre_push).
- Orçamento: < 60 s no repo-fixture (`tests/test_hook.py`, NFR8).

## CT11 — `bob update` e `bob --version` (v1)
**`bob update [--lang en|pt-BR]`** (dona U7, `src/bob_quality/update.py`; subcomando novo em `cli.py`).
- Roda na raiz git do projeto (mesma regra do passo `projeto`).
- Passos e saídas:
  | Id | Faz | Saída |
  |---|---|---|
  | `projeto` | raiz git | erro CT1, `4` |
  | `versão` | API `releases/latest` (CT14) → `tag_name` | erro `bob update: versão: não consegui ler a última release (<status>). Tente de novo.`, `4` |
  | `comparar` | pacote = `importlib.metadata.version("bob-quality")`; projeto = `.bob-version` das skills do bob (CT4) | ver abaixo |
  | `download` | `install.sh` e `SHA256SUMS` da tag (CT12); `Accept` só na API; textos en/pt em `update.*` (U7 `functional-design.md`) | erro, `4` |
  | `integridade` | sha256 do `install.sh` = linha do `SHA256SUMS` (bytes; 1ª linha cujo nome é `install.sh`); textos en/pt em `update.integrity` | erro, `4` |
  | `instalar` | `sh <install.sh> --lang <l>` com `BOB_VERSION=<tag>`, `cwd` = projeto | código do `install.sh` |
- Comparação por tupla numérica `(X, Y, Z)`:
  - pacote ≥ última **e** projeto ≥ última → stdout `bob update: já está na release mais nova (v<X.Y.Z>).`, `0`, 0 arquivos alterados (FR6.5).
  - pacote ≥ última e projeto < última ou sem skills → stdout `bob update: atualizando o projeto para v<X.Y.Z>.` e roda `bob setup` (sem download); código do `bob setup` (ver I3).
  - pacote < última → stdout `bob update: atualizando de v<A> para v<B>.` e segue para `download`.
- Nunca altera `bob.yaml`, `.bob/waivers.yaml`, hook alheio, skill alheia (CT3/CT4/CT7/CT10).

**`bob --version`** (top-level; `argparse.Action` própria com `nargs=0`; imprime e chama `parser.exit()` → `Help` no `_Parser`, sai `0` antes da exigência de subcomando; versão do pacote por `importlib.metadata.version("bob-quality")`):
```
bob <X.Y.Z>
project skills: <X.Y.Z> (.agents/skills)
```
- pt-BR: `skills do projeto: …`. Variações iguais às da linha do doctor (CT8): `not installed` / `não instaladas`, `mixed (…)` / `misturadas (…)`, inclusive `mixed (<v…>, not installed)` (Q1 = A).
- Projeto = `cwd`; não precisa ser raiz git. Lê só os nomes do manifesto empacotado (`manifest_skill_names`).

## CT12 — Formato de release (v1)
- Tag: `v<X.Y.Z>`, igual a `project.version` de `pyproject.toml` (hoje `0.1.0`, `pyproject.toml:7`). Tag nunca é reaproveitada.
- Assets (exatamente 3, nomes exatos):
  - `install.sh` — cópia byte a byte de `scripts/install.sh` do commit da tag.
  - `bob_quality-<X.Y.Z>-py3-none-any.whl` — `python -m build --wheel` (nome de distribuição normalizado para `bob_quality`).
  - `SHA256SUMS` — saída de `sha256sum install.sh bob_quality-<X.Y.Z>-py3-none-any.whl | LC_ALL=C sort -k2`: uma linha por arquivo, `<64 hex minúsculo><2 espaços><nome>\n` (formato padrão do GNU `sha256sum`, modo texto: https://www.gnu.org/software/coreutils/manual/html_node/md5sum-invocation.html, acessada 2026-10-18).
- URLs (padrão, sem `BOB_RELEASES_URL`):
  - última: `https://api.github.com/repos/fazedordecodigo/bob/releases/latest` → JSON, campo usado: `tag_name`.
  - asset: `https://github.com/fazedordecodigo/bob/releases/download/<tag>/<asset>`.
  - one-liner: `https://github.com/fazedordecodigo/bob/releases/latest/download/install.sh` (GitHub: sufixo `/releases/latest/download/<asset>` baixa o asset da última release; https://docs.github.com/en/repositories/releasing-projects-on-github/linking-to-releases, acessada 2026-10-18).
- Com `BOB_RELEASES_URL=<base>` (espelho e harness):
  - última: `<base>/api/releases/latest` → mesmo JSON (`{"tag_name": "vX.Y.Z", ...}`).
  - asset: `<base>/download/<tag>/<asset>`.
- Regra de "última": só release publicada. Pré-release e rascunho não contam (CT14). O espelho do harness segue a mesma regra.
- Conferência no cliente: pegar a linha cujo 2º campo é o nome do arquivo; comparar o hash com `sha256sum <arq>` (Linux) ou `shasum -a 256 <arq>` (macOS). Linha ausente = falha de integridade.

## CT13 — Workflow `release.yml` e release-check (v1)
**`.github/workflows/release.yml`** (dona U9).
- Gatilho: só `workflow_dispatch`, na `main` (`github.ref == 'refs/heads/main'`, senão falha no 1º job).
- Inputs:
  | Nome | Tipo | Padrão | Regra |
  |---|---|---|---|
  | `tag` | string | — (obrigatório) | `^v[0-9]+\.[0-9]+\.[0-9]+$`; `= "v" + pyproject version`; tag não existe ainda |
  | `prerelease` | boolean | `true` | `true` → `gh release create --prerelease --latest=false` |
  | `dry_run` | boolean | `false` | `true` → gera e anexa os 3 assets como artefato do run; não cria tag nem release |
- Jobs: `check` (inputs, versão) → `verify` (matriz Linux x64, Linux arm64, macOS x64, macOS arm64; roda o Comando de Verificação com os assets do run; rótulos de runner: **Não verificado**, ficam para o 3.7) → `publish` (só se `dry_run == false`; `permissions: contents: write` só aqui; `gh release create <tag> install.sh <wheel> SHA256SUMS --target <sha> --title <tag> --notes-file docs/release-checks/<tag>.md`).
- Fora desse workflow não se cria release (ADR 0011).

**Promoção (Q1 A do 2.7).** Sem rebuild: `gh release edit <tag> --repo fazedordecodigo/bob --prerelease=false --latest` (flags conferidos no manual do `gh release edit`, https://cli.github.com/manual/gh_release_edit, acessado 2026-10-18), ou pela interface. Assets e `SHA256SUMS` idênticos. Feita só pelo Emerson.

**`docs/release-checks/vX.Y.Z.md`** (modelo `docs/release-checks/TEMPLATE.md`).
```markdown
# Release check vX.Y.Z
- Commit: <sha>
- Run do release.yml: <url>
- Comando de Verificação: <passou|falhou> (<url do run>)

## Verificação manual (projeto do passo 2, skills só em .agents/skills)
| Agente | Data (UTC-3) | Versão do agente | Lista bob-check, harden, review-report uma vez? | Evidência |
|---|---|---|---|---|
| Cursor | | | | |
| Claude Code (RA1; ADR 0009 Risco 1) | | | | |
| GitHub Copilot | | | | |
| Devin CLI | | | | |
| Devin web | | | | |

## Prompt de IA (CT18, alternativa sem install.sh)
Um agente de IA real recebe `docs/install-prompt.<idioma>.md` num projeto novo e segue os passos. Conferir: não baixou nem rodou `install.sh`, não usou `sudo`, colou a saída de `setup` e `verificação`, e o resultado bate com o passo 2 (mesmos itens do manifesto do passo 14).
| Agente usado | Data (UTC-3) | Saída de `verificação` (`bob doctor` = 0, `bob --version`) | Sem `install.sh`/`sudo`? | Mesmo resultado do one-liner? | Evidência |
|---|---|---|---|---|---|
| | | | | | |

## Fluxo
- E2 antes de promover (`releases/latest` HTTP): <código>
- Promovida por: <nome>, em <data UTC-3>
- E6 depois de promover: `tag_name` = <tag>; `sha256sum -c SHA256SUMS`: <OK|falhou>
```
- Gatilho e resposta: `verification-command.md` do 2.6 ("Verificação manual por release") e U9 (`unit-of-work.md`).

## CT14 — APIs externas (v1)
| API | Endpoint | Resposta esperada | Erros e tratamento | Quem consome |
|---|---|---|---|---|
| GitHub REST: última release | `GET https://api.github.com/repos/fazedordecodigo/bob/releases/latest`, header `Accept: application/vnd.github+json` | `200`, JSON com `tag_name`. "The latest release is the most recent non-prerelease, non-draft release" (https://docs.github.com/en/rest/releases/releases#get-the-latest-release, acessada 2026-10-18) | `404` = não há release publicada (código listado na mesma página) → `versão` falha, `4`. `403`/`429` = limite (sem token: 60 req/h por IP; https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api, acessada 2026-10-18) → `4`, ação "tente de novo mais tarde" (sem oferecer `BOB_VERSION`; CT6). Retry no limite: `403` **nunca** é repetido (nem pelo `curl`, nem pelo Python). `429`: no `install.sh` (`CURL_OPTS` com `--retry 2`, CT18), o `curl` pode repetir até 2 vezes (trata `429` como transitório e respeita `Retry-After`), depois `4`; no Python (`bob update`), `429` não é repetido. Rede/timeout → 2 retries, depois `4` | U1 (`install.sh`), U7 (`bob update`), U9 (E2/E6) |
| GitHub: download de asset | `https://github.com/fazedordecodigo/bob/releases/download/<tag>/<asset>` (redireciona; `curl -L`, `urllib` segue) | `200` + bytes | `404` → asset ausente, `4` ("release incompleta; abra uma issue"); rede/timeout → 2 retries, `4` | U1, U7 |
| gitleaks releases | `https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/<asset>` | `200` + tar.gz com sha256 de CT9 | `404`/rede → `GitleaksError` download, `4`; sha diferente → integridade, `4` | U3 |
| Registro npm | o do `npm` do dev (padrão `https://registry.npmjs.org/`), via `npm ci --prefix <pacote>` com o `package-lock.json` empacotado | `npm ci` sai `0` | Sem mudança no tratamento atual (`npm_tools.py:133-154`): falha de escrita → cache do usuário; outra falha → mensagem atual e `4` | U1 (passo `npm`) |
| PyPI | o índice do `pip` do dev (padrão `https://pypi.org/simple`), para as dependências do wheel (`pyproject.toml:13-25`) | `pip install` sai `0` | `pip` ≠ 0 → passo `pacote`, `4`; `PIP_INDEX_URL` e afins respeitados | U1 (`install.sh`) |
- Tempos: `install.sh` usa `curl --connect-timeout 15 --max-time 300 --retry 2` (`CURL_OPTS`, fonte única do CT18): até 2 retries em timeout e em HTTP `408`, `429`, `500`, `502`, `503`, `504`; `403` e os outros `4xx` não são repetidos. Python (`bob update`, `gitleaks.py`) usa `urllib.request` com `timeout=30` por requisição e 2 retries só em erro de rede ou `5xx`; `4xx` (inclusive `429`) não tem retry.
- Nenhum token é lido ou enviado. Nada fala com `api.github.com` além do `releases/latest`.
- Rede off: falha no primeiro passo que precisa de rede, com a mensagem do passo; 0 arquivos do projeto mudam se for antes de `launcher`.

## CT16 — Perfil do shell (v2)
Dona U6. Passo `perfil` do `install.sh` (CT2), entre `launcher` e `setup`. Regra da ADR 0013 (Q1 A do 2.6).
- Roda só se `:$PATH:` não contém `:$HOME/.local/bin:`. Senão, resultado `already-on-path`, nada escrito.
- Arquivo: `basename "$SHELL"` = `zsh` → `${ZDOTDIR:-$HOME}/.zshrc`; `bash` → `$HOME/.bashrc`; outro ou vazio → `$HOME/.profile`.
- Linha (exata, CT5): `export PATH="$HOME/.local/bin:$PATH" # managed-by: bob-quality`
- Arquivo já tem `# managed-by: bob-quality` → `already-marked:<arquivo absoluto>`, nada escrito.
- Arquivo não existe → cria só com a linha + `\n`, modo `0644` → resultado `<arquivo absoluto>`.
- Arquivo existe → acrescenta no fim (com `\n` antes se o último byte não é `\n`); bytes anteriores iguais → `<arquivo absoluto>`. Symlink: escreve no destino.
- Falha de escrita (criar, `chmod 0644` ou acrescentar) → `failed:<arquivo absoluto>` e aviso no stdout (en): `install: perfil: warning: could not write <arquivo> (<erro>). To use the bob command, add to your profile: export PATH="$HOME/.local/bin:$PATH".` pt-BR: `install: perfil: aviso: não consegui gravar <arquivo> (<erro>). Para usar o comando bob, acrescente ao seu perfil: export PATH="$HOME/.local/bin:$PATH".` `<erro>` = texto depois do último `": "` da 1ª linha do stderr do shell, ou `unknown error` / `erro desconhecido`. O código de saída não muda; o passo sempre imprime `install: perfil: ok`.
- Saída para o `bob setup`: `export BOB_INSTALL_PROFILE=<resultado>` e depois `exec` (CT2, ADR 0022); o texto do resumo está em CT3.
- `bob update` não roda este passo de novo com efeito (o arquivo já tem a marca).

## CT17 — Docs de instalação e teste de paridade (v1)
Dona U8.
- Arquivos (8; ADR 0028): `README.md`, `README.pt-BR.md`, `docs/getting-started/installation.md`, `website/i18n/pt-BR/docusaurus-plugin-content-docs/current/getting-started/installation.md` (no lugar de `docs/instalacao.md`, removido no #174), `docs/getting-started/agents.md`, `website/i18n/pt-BR/…/getting-started/agents.md`, `docs/guides/pre-push.md`, `website/i18n/pt-BR/…/guides/pre-push.md`. Os 4 primeiros são os docs de instalação.
- Em cada um, o primeiro **bloco de shell** (info string cuja 1ª palavra é `bash`, `sh`, `shell` ou `console`; fica de fora o `mermaid` do README) é o one-liner exato de CT2/CT12 (en: `… | sh`; pt-BR: `… | sh -s -- --lang pt-BR`). Sem `git clone` e sem plugin antes dele.
- **Ordem dos caminhos** (origem: Emerson, via Maestro, 18/10/2026 19:14 (UTC-3), literal: (1) "Adicione um prompt que orie te um modelo de IA a como instalar passo a passo o pacote sem depender de um arquivo .sh"; (2) "Deve haver as duas opções a principal sendo o arquivo .sh"). Nos 4 docs de instalação (`README.md`, `README.pt-BR.md`, `docs/getting-started/installation.md`, página pt-BR do site):
  1. primeiro, o one-liner do `install.sh` (CT2), apresentado como caminho principal;
  2. depois, numa seção própria marcada como alternativa (pt-BR: `### Alternativa: pedir ao seu agente de IA`; en: `### Alternative: ask your AI agent`), um parágrafo que diz que o caminho não usa o `install.sh`, chega ao mesmo resultado e que, em divergência, vale o comando principal, e o link para o arquivo do prompt no idioma do doc (CT18). Links: `README.md` → `docs/install-prompt.en.md`; `README.pt-BR.md` → `docs/install-prompt.pt-BR.md`; `docs/getting-started/installation.md` → `../install-prompt.en.md`; página pt-BR do site → `/install-prompt.pt-BR.md` (com `/`; ADR 0028). O teste resolve: com `/`, a partir de `docs/`; sem `/`, a partir da pasta do arquivo.
  3. depois da alternativa, seção `## Update` / `## Atualizar` com um bloco `bash` de exatamente 2 linhas (`bob update` e `bob --version`) (FR8.3, ADR 0029).
  - O doc traz o link, não o prompt inteiro. A ordem e o teste de ordem ficam iguais.
- `docs/getting-started/agents.md` diz: pasta única `.agents/skills`; Claude Code sob RA1.
- `tests/test_docs_pins.py`:
  - toda versão de ferramenta npm citada nos 8 arquivos = `pinned_npm_versions()` (CT8);
  - faixa do Node citada = `str(node_range())`;
  - versão do gitleaks citada = `gitleaks.VERSION` (CT9);
  - piso do Python citado = `requires-python` de `pyproject.toml`;
  - o one-liner citado = o de CT12;
  - ordem: nos 4 docs de instalação, a posição do one-liner é menor que a do título da alternativa, e o título existe uma vez;
  - a seção da alternativa tem o link por arquivo (ADR 0028), e o arquivo existe;
  - os 11 itens de paridade do CT18 (blocos do prompt × fontes únicas; `BOB_VERSION` só em nota de testes);
  - `BOB_VERSION` nos 8 docs: só dentro de uma nota marcada `Somente testes/release-check` / `Tests/release-check only` (uso normal = última release publicada, FR1.4);
  - sai `0` só se tudo bate. A U9 roda esse teste no `release.yml` (dentro do `pytest`).

## CT18 — Prompt de instalação para agente de IA, sem `install.sh` (v1)
Dona U8. Origem: Emerson, via Maestro, 18/10/2026 19:14 (UTC-3), literal: (1) "Adicione um prompt que orie te um modelo de IA a como instalar passo a passo o pacote sem depender de um arquivo .sh"; (2) "Deve haver as duas opções a principal sendo o arquivo .sh".

**Posição.**
- Alternativa ao CT2. **Nunca substituto.** O caminho principal é o one-liner do `install.sh`.
- Em divergência entre o prompt e o CT2, **o CT2 manda**: o CT18 é corrigido para bater com o CT2. Mudança no CT2 (ou no CT3, CT5, CT9, CT12, CT16) obriga a revisar o CT18 no mesmo PR; o teste de paridade (CT17) falha se não revisar.
- Os docs mostram primeiro o one-liner e depois a alternativa (CT17).
- O prompt **não baixa nem executa** `install.sh`. Cada passo do CT2 vira um passo do prompt, com comando exato. O teste confere que nenhum bloco cita `install.sh` nem `sudo`.

**Arquivos.** `docs/install-prompt.en.md` e `docs/install-prompt.pt-BR.md`. O dev cola o arquivo inteiro no agente. Não é asset da release (CT12 continua com 3 assets): o prompt baixa só o wheel e o `SHA256SUMS`, que já são assets, e o texto vive no repo com versão junto do código.

**Versão instalada.** Sempre a última release publicada (`releases/latest`, FR1.4, CT14). O texto do prompt para o dev não oferece `BOB_VERSION`: a seção `Regras` e os títulos dos passos não a citam, e as mensagens dos blocos também não (falha de leitura diz só "try again later"). O bloco `versão` lê `${BOB_VERSION:-}` só para que o mesmo prompt sirva ao harness e ao release-check da pré-release (Q1 A do 2.7, E3 do U9: a pré-release não é `latest`). Isso aparece no fim do arquivo, numa nota única, exata:
- pt-BR: `> Somente testes/release-check: BOB_VERSION=vX.Y.Z fixa a tag (ex.: pré-release no release-check). Fora disso, não defina; o prompt instala a última release publicada.`
- en: `> Tests/release-check only: BOB_VERSION=vX.Y.Z pins the tag (e.g. a pre-release in the release-check). Otherwise, do not set it; the prompt installs the latest published release.`

**Formato do arquivo (os dois idiomas).**
1. Título e um aviso: `Caminho alternativo. O principal é o comando único do install.sh; em divergência, vale ele.` (en: `Alternative path. The main path is the install.sh one-liner; if they differ, the one-liner wins.`).
2. A seção `Regras` (texto abaixo).
3. Um título por passo, `## <n>. <id>`, seguido de um ou mais blocos de código. Info string de cada bloco, exata: `sh bob-step=<id> platform=<p>`, com `<p>` ∈ `all`, `linux`, `darwin`, `linux-x64`, `linux-arm64`, `darwin-x64`, `darwin-arm64`. O GitHub mostra como `sh` (só a 1ª palavra da info string vira linguagem; CommonMark 0.31.2, §4.5 "Fenced code blocks", https://spec.commonmark.org/0.31.2/#fenced-code-blocks, acessada 2026-10-18).
4. Os blocos são **byte a byte iguais** nos dois idiomas. Só a prosa muda. As mensagens dos blocos são em inglês, com prefixo `bob-prompt: <passo>:` (não fingem ser o `install.sh`).

**Regras (texto do prompt; pt-BR exato, en com o mesmo conteúdo).**
```text
Você vai instalar o bob (https://github.com/fazedordecodigo/bob) neste projeto, sem o install.sh. Regras:
1. Nunca use sudo.
2. Não baixe nem execute install.sh. Não clone o repositório do bob. Não instale plugin de agente.
3. Nunca pule nem altere uma conferência de sha256.
4. Rode os blocos na ordem, na raiz do projeto, um bloco por comando de shell, sem editar nenhum bloco. Cada bloco é independente; o estado fica em ${TMPDIR:-/tmp}/bob-install-<uid>.
5. Depois do passo "plataforma", rode só os blocos com platform=all, com o seu sistema (linux ou darwin) ou com a plataforma que ele imprimiu.
6. Se um bloco sair com código diferente de 0: pare. Mostre ao humano a saída completa do bloco. Não tente contornar, não tente outro caminho.
7. No fim, cole a saída completa dos passos "setup" e "verificação".
8. Para mensagens do bob em pt-BR, rode os passos "setup" e "verificação" com BOB_LANG=pt-BR.
```
- en: mesma lista; padrão de idioma `en`, como o CT2.

**Preâmbulo.** Todo bloco começa com estas 6 linhas, exatas. Elas calculam `BOB_HOME` com a regra do CT5/CT6 (`bob_home()`) e o diretório de estado `W`, fora do `HOME` e do projeto:
```sh
set -eu
fail() { printf 'bob-prompt: %s\n' "$*" >&2; exit 4; }
case "${XDG_DATA_HOME:-}" in /*) D="$XDG_DATA_HOME" ;; *) D="$HOME/.local/share" ;; esac
BOB_HOME="${BOB_HOME:-$D/bob-quality}"
case "$BOB_HOME" in /*) ;; *) fail "launcher: BOB_HOME=$BOB_HOME must be absolute" ;; esac
W="${TMPDIR:-/tmp}/bob-install-$(id -u)"
```

**Passos (corpo de cada bloco, depois do preâmbulo).**
### 1. `projeto` (CT2: `projeto`)
```sh bob-step=projeto platform=all
command -v git >/dev/null 2>&1 || fail "projeto: git not found; install git and run again"
top=$(git rev-parse --show-toplevel 2>/dev/null) || fail "projeto: $(pwd -P) is not the root of a git repository; run in the project root"
[ "$top" = "$(pwd -P)" ] || fail "projeto: $(pwd -P) is not the root of a git repository; run in the project root"
rm -rf "$W" && mkdir -p "$W" && pwd -P > "$W/project"
echo "bob-prompt: projeto: ok"
```
### 2. `plataforma` (CT2: `plataforma`)
```sh bob-step=plataforma platform=all
s=$(uname -s); m=$(uname -m)
case "$s/$m" in
  Linux/x86_64|Linux/amd64) p=linux-x64 ;;
  Linux/aarch64|Linux/arm64) p=linux-arm64 ;;
  Darwin/x86_64) p=darwin-x64 ;;
  Darwin/arm64) p=darwin-arm64 ;;
  *) fail "plataforma: $s/$m is not supported; supported: Linux and macOS, x64 and arm64" ;;
esac
printf '%s\n' "$p" > "$W/platform"
echo "bob-prompt: plataforma: $p"
```
### 3. `python` (CT2: `python`)
```sh bob-step=python platform=all
command -v python3 >/dev/null 2>&1 || fail "python: python3 not found; install Python 3.10 or newer"
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || fail "python: found $(python3 -c 'import platform; print(platform.python_version())'), required >=3.10"
python3 -c 'import venv, ensurepip' 2>/dev/null || fail "python: the venv module is not available; on Ubuntu, install python3-venv"
echo "bob-prompt: python: ok"
```
### 4. `node` (CT2: `node`)
```sh bob-step=node platform=all
# node: >=22.18.0 <23
command -v node >/dev/null 2>&1 || fail "node: node not found; install Node >=22.18.0 <23"
command -v npm >/dev/null 2>&1 || fail "node: npm not found; install npm with Node"
v=$(node --version)
printf '%s\n' "$v" | grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+$' || fail "node: found $v, required >=22.18.0 <23"
python3 -c 'import sys; v = tuple(int(x) for x in sys.argv[1][1:].split(".")); sys.exit(0 if (22, 18, 0) <= v < (23,) else 1)' "$v" || fail "node: found $v, required >=22.18.0 <23"
echo "bob-prompt: node: ok"
```
### 5. `ferramentas` (CT2: `ferramentas`)
```sh bob-step=ferramentas platform=linux
command -v curl >/dev/null 2>&1 || fail "ferramentas: curl not found; install curl and run again"
command -v sha256sum >/dev/null 2>&1 || fail "ferramentas: sha256sum not found; install coreutils and run again"
echo "bob-prompt: ferramentas: ok"
```
```sh bob-step=ferramentas platform=darwin
command -v curl >/dev/null 2>&1 || fail "ferramentas: curl not found; install curl and run again"
command -v shasum >/dev/null 2>&1 || fail "ferramentas: shasum not found; install it and run again"
echo "bob-prompt: ferramentas: ok"
```
### 6. `versão` (CT2: `versão`)
```sh bob-step=versão platform=all
if [ -n "${BOB_RELEASES_URL:-}" ]; then
  R=${BOB_RELEASES_URL%/}
  case "$R" in https://*|http://127.0.0.1|http://127.0.0.1[:/]*|http://localhost|http://localhost[:/]*) ;; *) fail "versão: BOB_RELEASES_URL=$R is not allowed (https, or http only on 127.0.0.1/localhost)" ;; esac
  API="$R/api/releases/latest"; DL="$R/download"
else
  API="https://api.github.com/repos/fazedordecodigo/bob/releases/latest"; DL="https://github.com/fazedordecodigo/bob/releases/download"
fi
if [ -n "${BOB_VERSION:-}" ]; then
  V=$BOB_VERSION
else
  V=$(curl -fsSL --connect-timeout 15 --max-time 300 --retry 2 -H 'Accept: application/vnd.github+json' "$API" | python3 -c 'import json, sys; print(json.load(sys.stdin)["tag_name"])') || fail "versão: could not read the latest release; try again later"
fi
printf '%s\n' "$V" | grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+$' || fail "versão: $V is not a valid tag (vX.Y.Z)"
printf '%s\n' "$V" > "$W/version"
printf '%s\n' "$DL" > "$W/dl"
echo "bob-prompt: versão: $V"
```
### 7. `download` (CT2: `download`)
```sh bob-step=download platform=all
V=$(cat "$W/version"); DL=$(cat "$W/dl"); WHL="bob_quality-${V#v}-py3-none-any.whl"
for f in "$WHL" SHA256SUMS; do
  curl -fsSL --connect-timeout 15 --max-time 300 --retry 2 -o "$W/$f" "$DL/$V/$f" || fail "download: $DL/$V/$f failed; check the network and try again"
done
echo "bob-prompt: download: ok"
```
### 8. `integridade` (CT2: `integridade`)
```sh bob-step=integridade platform=linux
V=$(cat "$W/version"); WHL="bob_quality-${V#v}-py3-none-any.whl"
want=$(awk -v f="$WHL" '$2 == f { print $1 }' "$W/SHA256SUMS")
got=$(sha256sum "$W/$WHL" | awk '{ print $1 }')
[ -n "$want" ] && [ "$want" = "$got" ] || fail "integridade: the sha256 of $WHL does not match; nothing was installed"
printf '%s\n' "$got" > "$W/wheel.sha256"
echo "bob-prompt: integridade: ok"
```
```sh bob-step=integridade platform=darwin
V=$(cat "$W/version"); WHL="bob_quality-${V#v}-py3-none-any.whl"
want=$(awk -v f="$WHL" '$2 == f { print $1 }' "$W/SHA256SUMS")
got=$(shasum -a 256 "$W/$WHL" | awk '{ print $1 }')
[ -n "$want" ] && [ "$want" = "$got" ] || fail "integridade: the sha256 of $WHL does not match; nothing was installed"
printf '%s\n' "$got" > "$W/wheel.sha256"
echo "bob-prompt: integridade: ok"
```
### 9. `pacote` (CT2: `pacote`)
```sh bob-step=pacote platform=all
V=$(cat "$W/version"); X=${V#v}; WHL="bob_quality-$X-py3-none-any.whl"
H=$(cat "$W/wheel.sha256"); VD="$BOB_HOME/versions/$X"
if [ -f "$VD/.complete" ] && [ "$(cat "$VD/.complete")" = "$H" ]; then
  echo "bob-prompt: pacote: ok (reused)"
else
  rm -rf "$VD" && mkdir -p "$VD"
  { python3 -m venv "$VD/venv" && "$VD/venv/bin/pip" install --disable-pip-version-check --no-input "$W/$WHL"; } || { rm -rf "$VD"; fail "pacote: pip failed; see the output above and try again"; }
  printf '%s\n' "$H" > "$VD/.complete"
  echo "bob-prompt: pacote: ok"
fi
```
### 10. `launcher` (CT2: `launcher`)
```sh bob-step=launcher platform=all
V=$(cat "$W/version"); X=${V#v}; L="$HOME/.local/bin/bob"
mkdir -p "$BOB_HOME/bin" "$HOME/.local/bin" || fail "launcher: could not create $BOB_HOME/bin or $HOME/.local/bin"
rm -f "$BOB_HOME/current.tmp"
ln -s "versions/$X" "$BOB_HOME/current.tmp" || fail "launcher: could not create $BOB_HOME/current.tmp"
"$BOB_HOME/versions/$X/venv/bin/python" -c 'import os, sys; os.replace(sys.argv[1], sys.argv[2])' "$BOB_HOME/current.tmp" "$BOB_HOME/current" || fail "launcher: could not create $BOB_HOME/current"
ln -sfn ../current/venv/bin/bob "$BOB_HOME/bin/bob" || fail "launcher: could not create $BOB_HOME/bin/bob"
if [ -L "$L" ] && [ "$(readlink "$L")" = "$BOB_HOME/bin/bob" ]; then
  :
elif [ -e "$L" ] || [ -L "$L" ]; then
  echo "bob-prompt: launcher: warning: $L already exists and is not bob's; left as is"
else
  ln -s "$BOB_HOME/bin/bob" "$L" || fail "launcher: could not create $L"
fi
echo "bob-prompt: launcher: ok"
```
### 11. `gitleaks` (CT2: `setup` → passo 4 do CT3 (`gitleaks`))
```sh bob-step=gitleaks platform=linux-x64
A=gitleaks_8.30.1_linux_x64.tar.gz
S=551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb
G="$BOB_HOME/tools/gitleaks/8.30.1"
GB=${BOB_GITLEAKS_BASE_URL:-https://github.com/gitleaks/gitleaks/releases/download/v8.30.1}; GB=${GB%/}
case "$GB" in https://*|http://127.0.0.1|http://127.0.0.1[:/]*|http://localhost|http://localhost[:/]*) ;; *) fail "gitleaks: BOB_GITLEAKS_BASE_URL=$GB is not allowed" ;; esac
if [ -x "$BOB_HOME/bin/gitleaks" ] && "$BOB_HOME/bin/gitleaks" --version 2>/dev/null | grep -qF 8.30.1; then
  echo "bob-prompt: gitleaks: ok (reused)"
else
  curl -fsSL --connect-timeout 15 --max-time 300 --retry 2 -o "$W/$A" "$GB/$A" || fail "gitleaks: download of $GB/$A failed; check the network and try again"
  [ "$(sha256sum "$W/$A" | awk '{ print $1 }')" = "$S" ] || fail "gitleaks: the sha256 of $A does not match; nothing was installed"
  rm -rf "$W/gl" && mkdir "$W/gl"
  tar -xzf "$W/$A" -C "$W/gl" gitleaks 2>/dev/null || fail "gitleaks: $A does not have the expected gitleaks binary; nothing was installed"
  [ -f "$W/gl/gitleaks" ] && [ ! -L "$W/gl/gitleaks" ] || fail "gitleaks: $A does not have the expected gitleaks binary; nothing was installed"
  mkdir -p "$G" "$BOB_HOME/bin"
  cp "$W/gl/gitleaks" "$G/gitleaks.tmp" && chmod 0755 "$G/gitleaks.tmp" && mv -f "$G/gitleaks.tmp" "$G/gitleaks"
  ln -sfn ../tools/gitleaks/8.30.1/gitleaks "$BOB_HOME/bin/gitleaks"
  echo "bob-prompt: gitleaks: ok"
fi
```
```sh bob-step=gitleaks platform=linux-arm64
A=gitleaks_8.30.1_linux_arm64.tar.gz
S=e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080
G="$BOB_HOME/tools/gitleaks/8.30.1"
GB=${BOB_GITLEAKS_BASE_URL:-https://github.com/gitleaks/gitleaks/releases/download/v8.30.1}; GB=${GB%/}
case "$GB" in https://*|http://127.0.0.1|http://127.0.0.1[:/]*|http://localhost|http://localhost[:/]*) ;; *) fail "gitleaks: BOB_GITLEAKS_BASE_URL=$GB is not allowed" ;; esac
if [ -x "$BOB_HOME/bin/gitleaks" ] && "$BOB_HOME/bin/gitleaks" --version 2>/dev/null | grep -qF 8.30.1; then
  echo "bob-prompt: gitleaks: ok (reused)"
else
  curl -fsSL --connect-timeout 15 --max-time 300 --retry 2 -o "$W/$A" "$GB/$A" || fail "gitleaks: download of $GB/$A failed; check the network and try again"
  [ "$(sha256sum "$W/$A" | awk '{ print $1 }')" = "$S" ] || fail "gitleaks: the sha256 of $A does not match; nothing was installed"
  rm -rf "$W/gl" && mkdir "$W/gl"
  tar -xzf "$W/$A" -C "$W/gl" gitleaks 2>/dev/null || fail "gitleaks: $A does not have the expected gitleaks binary; nothing was installed"
  [ -f "$W/gl/gitleaks" ] && [ ! -L "$W/gl/gitleaks" ] || fail "gitleaks: $A does not have the expected gitleaks binary; nothing was installed"
  mkdir -p "$G" "$BOB_HOME/bin"
  cp "$W/gl/gitleaks" "$G/gitleaks.tmp" && chmod 0755 "$G/gitleaks.tmp" && mv -f "$G/gitleaks.tmp" "$G/gitleaks"
  ln -sfn ../tools/gitleaks/8.30.1/gitleaks "$BOB_HOME/bin/gitleaks"
  echo "bob-prompt: gitleaks: ok"
fi
```
```sh bob-step=gitleaks platform=darwin-x64
A=gitleaks_8.30.1_darwin_x64.tar.gz
S=dfe101a4db2255fc85120ac7f3d25e4342c3c20cf749f2c20a18081af1952709
G="$BOB_HOME/tools/gitleaks/8.30.1"
GB=${BOB_GITLEAKS_BASE_URL:-https://github.com/gitleaks/gitleaks/releases/download/v8.30.1}; GB=${GB%/}
case "$GB" in https://*|http://127.0.0.1|http://127.0.0.1[:/]*|http://localhost|http://localhost[:/]*) ;; *) fail "gitleaks: BOB_GITLEAKS_BASE_URL=$GB is not allowed" ;; esac
if [ -x "$BOB_HOME/bin/gitleaks" ] && "$BOB_HOME/bin/gitleaks" --version 2>/dev/null | grep -qF 8.30.1; then
  echo "bob-prompt: gitleaks: ok (reused)"
else
  curl -fsSL --connect-timeout 15 --max-time 300 --retry 2 -o "$W/$A" "$GB/$A" || fail "gitleaks: download of $GB/$A failed; check the network and try again"
  [ "$(shasum -a 256 "$W/$A" | awk '{ print $1 }')" = "$S" ] || fail "gitleaks: the sha256 of $A does not match; nothing was installed"
  rm -rf "$W/gl" && mkdir "$W/gl"
  tar -xzf "$W/$A" -C "$W/gl" gitleaks 2>/dev/null || fail "gitleaks: $A does not have the expected gitleaks binary; nothing was installed"
  [ -f "$W/gl/gitleaks" ] && [ ! -L "$W/gl/gitleaks" ] || fail "gitleaks: $A does not have the expected gitleaks binary; nothing was installed"
  mkdir -p "$G" "$BOB_HOME/bin"
  cp "$W/gl/gitleaks" "$G/gitleaks.tmp" && chmod 0755 "$G/gitleaks.tmp" && mv -f "$G/gitleaks.tmp" "$G/gitleaks"
  ln -sfn ../tools/gitleaks/8.30.1/gitleaks "$BOB_HOME/bin/gitleaks"
  echo "bob-prompt: gitleaks: ok"
fi
```
```sh bob-step=gitleaks platform=darwin-arm64
A=gitleaks_8.30.1_darwin_arm64.tar.gz
S=b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5
G="$BOB_HOME/tools/gitleaks/8.30.1"
GB=${BOB_GITLEAKS_BASE_URL:-https://github.com/gitleaks/gitleaks/releases/download/v8.30.1}; GB=${GB%/}
case "$GB" in https://*|http://127.0.0.1|http://127.0.0.1[:/]*|http://localhost|http://localhost[:/]*) ;; *) fail "gitleaks: BOB_GITLEAKS_BASE_URL=$GB is not allowed" ;; esac
if [ -x "$BOB_HOME/bin/gitleaks" ] && "$BOB_HOME/bin/gitleaks" --version 2>/dev/null | grep -qF 8.30.1; then
  echo "bob-prompt: gitleaks: ok (reused)"
else
  curl -fsSL --connect-timeout 15 --max-time 300 --retry 2 -o "$W/$A" "$GB/$A" || fail "gitleaks: download of $GB/$A failed; check the network and try again"
  [ "$(shasum -a 256 "$W/$A" | awk '{ print $1 }')" = "$S" ] || fail "gitleaks: the sha256 of $A does not match; nothing was installed"
  rm -rf "$W/gl" && mkdir "$W/gl"
  tar -xzf "$W/$A" -C "$W/gl" gitleaks 2>/dev/null || fail "gitleaks: $A does not have the expected gitleaks binary; nothing was installed"
  [ -f "$W/gl/gitleaks" ] && [ ! -L "$W/gl/gitleaks" ] || fail "gitleaks: $A does not have the expected gitleaks binary; nothing was installed"
  mkdir -p "$G" "$BOB_HOME/bin"
  cp "$W/gl/gitleaks" "$G/gitleaks.tmp" && chmod 0755 "$G/gitleaks.tmp" && mv -f "$G/gitleaks.tmp" "$G/gitleaks"
  ln -sfn ../tools/gitleaks/8.30.1/gitleaks "$BOB_HOME/bin/gitleaks"
  echo "bob-prompt: gitleaks: ok"
fi
```
### 12. `perfil` (CT2: `perfil`)
```sh bob-step=perfil platform=all
LINE='export PATH="$HOME/.local/bin:$PATH" # managed-by: bob-quality'
case ":$PATH:" in
  *":$HOME/.local/bin:"*) R=already-on-path ;;
  *)
    S=${SHELL:-}
    case "${S##*/}" in
      zsh) F="${ZDOTDIR:-$HOME}/.zshrc" ;;
      bash) F="$HOME/.bashrc" ;;
      *) F="$HOME/.profile" ;;
    esac
    if [ -f "$F" ] && grep -qF '# managed-by: bob-quality' "$F"; then
      R="already-marked:$F"
    elif { [ -e "$F" ] || { : > "$F" && chmod 0644 "$F"; }; } 2>/dev/null && { if [ -s "$F" ] && [ -n "$(tail -c 1 "$F")" ]; then printf '\n'; fi; printf '%s\n' "$LINE"; } >> "$F" 2>/dev/null; then
      R=$F
    else
      R="failed:$F"
      echo "bob-prompt: perfil: warning: could not write $F. To use the bob command, add to your profile: export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi ;;
esac
printf '%s\n' "$R" > "$W/profile"
echo "bob-prompt: perfil: $R"
```
### 13. `setup` (CT2: `setup`)
```sh bob-step=setup platform=all
[ "$(pwd -P)" = "$(cat "$W/project")" ] || fail "setup: run this block in the project root $(cat "$W/project")"
BOB_INSTALL_PROFILE="$(cat "$W/profile")" "$BOB_HOME/bin/bob" setup --lang "${BOB_LANG:-en}" || fail "setup: bob setup exited $?; see the output above"
```
### 14. `verificação` (CT2: `setup` → passo 8 do CT3 (`doctor`) + passo 2 do Comando)
```sh bob-step=verificação platform=all
V=$(cat "$W/version"); X=${V#v}
if "$BOB_HOME/bin/bob" doctor; then d=0; else d=$?; fi
BOB_LANG=en "$BOB_HOME/bin/bob" --version > "$W/version.out" || fail "verificação: bob --version failed"
cat "$W/version.out"
[ "$d" -eq 0 ] || fail "verificação: bob doctor exited $d, expected 0"
[ "$(sed -n 1p "$W/version.out")" = "bob $X" ] || fail "verificação: bob --version does not show bob $X"
[ "$(sed -n 2p "$W/version.out")" = "project skills: $X (.agents/skills)" ] || fail "verificação: project skills are not at $X"
rm -rf "$W"
echo "bob-prompt: verificação: ok (bob $X, bob doctor 0)"
```

**Tabela de equivalência (prompt ↔ `install.sh`).**
| # | Passo do prompt | Passo do CT2 | Plataforma | Nota |
|---|---|---|---|---|
| 1 | `projeto` | `projeto` | all | — |
| 2 | `plataforma` | `plataforma` | all | só a tabela do CT9 (Darwin aceita só `x86_64`/`arm64`; o CT2 aceita também `amd64`/`aarch64`, que o macOS não reporta) |
| 3 | `python` | `python` | all | — |
| 4 | `node` | `node` | all | faixa `str(node_range())` do CT8 |
| 5 | `ferramentas` | `ferramentas` | linux, darwin | Linux exige `sha256sum`; macOS exige `shasum` (o CT2 aceita qualquer um dos dois) |
| 6 | `versão` | `versão` | all | CT6/CT14; mesma regra de `BOB_RELEASES_URL` |
| 7 | `download` | `download` | all | CT12 |
| 8 | `integridade` | `integridade` | linux, darwin | CT12, `sha256sum` (Linux) / `shasum -a 256` (macOS) |
| 9 | `pacote` | `pacote` | all | CT5: `versions/<X.Y.Z>/venv`, `.complete` por último, reuso |
| 10 | `launcher` | `launcher` | all | CT5: `current` por `os.replace`, `bin/bob`, `~/.local/bin/bob` |
| 11 | `gitleaks` | `setup` → passo 4 do CT3 (`gitleaks`) | linux-x64, linux-arm64, darwin-x64, darwin-arm64 | antecipado; o `bob setup` encontra o binário e faz 0 downloads (CT9) |
| 12 | `perfil` | `perfil` | all | CT16, mesma linha e idempotência |
| 13 | `setup` | `setup` | all | CT3; código ≠ 0 → `4` |
| 14 | `verificação` | `setup` → passo 8 do CT3 (`doctor`) + passo 2 do Comando | all | `bob doctor` = 0 e `bob --version` = alvo |
- Os 12 passos do CT2 aparecem uma vez cada, na mesma ordem. Os 2 a mais (`gitleaks`, `verificação`) são passos do `bob setup` (CT3) que o prompt deixa visíveis; não criam estado que o `install.sh` não cria.

**Mesmo resultado.** Depois do passo `verificação`, o estado é o mesmo de uma instalação pelo `install.sh` com o mesmo env:
- caminhos e symlinks do CT5 (`versions/<X.Y.Z>/venv`, `.complete` = sha256 do wheel + `\n`, `current -> versions/<X.Y.Z>`, `bin/bob -> ../current/venv/bin/bob`, `~/.local/bin/bob -> $BOB_HOME/bin/bob`, `bin/gitleaks -> ../tools/gitleaks/8.30.1/gitleaks`, binário `0755`);
- marcadores do CT5 e linha do perfil do CT16; resultado do perfil passado ao `bob setup` em `BOB_INSTALL_PROFILE`;
- versões: wheel da tag, gitleaks 8.30.1, npm do `package-lock.json` empacotado (o `bob setup` instala);
- projeto: o `bob setup` (CT3) faz skills, `bob.yaml` e hook, igual ao CT2.
- Diferenças permitidas (não mudam o estado final): prefixo `bob-prompt:` e mensagens só em inglês nos blocos; `W` fica em disco se um passo falha (para o humano ver); Darwin `amd64`/`aarch64` recusado no passo `plataforma` (o CT9 recusaria no `gitleaks` de qualquer jeito).
- Teste nesta sessão (box Linux x64, 2026-10-18): os blocos passam em `dash -n`; `projeto`, `plataforma`, `python`, `ferramentas`, `versão` (com `BOB_VERSION`), `launcher` (2×), `gitleaks` (download real da v8.30.1, sha confere, 2ª vez reusa, `gitleaks version 8.30.1`), `perfil` (bash cria `.bashrc` `0644`; zsh acrescenta `\n` antes; 2ª vez `already-marked`; `already-on-path`) e `integridade` (passa; wheel trocado → `4`) se comportaram como acima; `node` recusou o Node 24 com `4`. `pacote`, `setup` e `verificação` dependem do wheel do U1; quem prova é o passo 14 proposto.

**Paridade (teste do CT17, `tests/test_docs_pins.py`).** Fontes únicas que o `scripts/install.sh` passa a declarar, uma linha cada, no topo (acréscimo compatível ao CT2): `STEPS='projeto plataforma python node ferramentas versão download integridade pacote launcher perfil setup'`, `PROFILE_LINE='export PATH="$HOME/.local/bin:$PATH" # managed-by: bob-quality'`, `DEFAULT_API='https://api.github.com/repos/fazedordecodigo/bob/releases/latest'`, `DEFAULT_DOWNLOAD='https://github.com/fazedordecodigo/bob/releases/download'`, `CURL_OPTS='-fsSL --connect-timeout 15 --max-time 300 --retry 2'`, `PIP_OPTS='--disable-pip-version-check --no-input'`. O teste lê cada uma com `^NOME='(.*)'$`.
- **Extração dos blocos:** `re.finditer(r"^```sh bob-step=(?P<id>\S+) platform=(?P<p>\S+)\n(?P<body>.*?)^```$", texto, re.M | re.S)`. Bloco com outra info string não conta. Fora dos blocos, nada é comando.
- Confere, e falha com a diferença:
  1. en e pt-BR têm a mesma lista de `(id, platform, body)`.
  2. ids em ordem (sem repetição) = `STEPS` com `gitleaks` depois de `launcher` e `verificação` no fim. Passo faltando, sobrando ou fora de ordem falha.
  3. por id, as plataformas cobrem `linux-x64`, `linux-arm64`, `darwin-x64`, `darwin-arm64` uma vez cada (`all` = 4, `linux`/`darwin` = 2).
  4. todo bloco começa com o preâmbulo, igual entre blocos. O teste roda o preâmbulo em `sh` com `printf %s "$BOB_HOME"` para 4 envs (nada; `XDG_DATA_HOME` absoluto; `XDG_DATA_HOME` relativo; `BOB_HOME` absoluto) e compara com `bob_home(env).root`; `BOB_HOME` relativo → o `sh` sai `4` e `bob_home` dá `ValueError`.
  5. gitleaks: em cada bloco, `A=` e `S=` = `gitleaks.ASSETS[platform_key(...)]`; toda versão citada = `gitleaks.VERSION`; base padrão = `https://github.com/gitleaks/gitleaks/releases/download/v{VERSION}`.
  6. `node`: comentário `# node: <str(node_range())>` e as tuplas `(22, 18, 0)` e `(23,)` derivadas de `node_range()`. `python`: `(3, 10)` = piso de `requires-python`.
  7. layout: o bloco `launcher` tem `ln -s "versions/$X"`, `ln -sfn ../current/venv/bin/bob` e `L="$HOME/.local/bin/bob"`; o `gitleaks` tem `../tools/gitleaks/{VERSION}/gitleaks`; o `pacote` grava `.complete` depois do `pip`.
  8. `perfil`: `LINE=` = `PROFILE_LINE`; marcador = `# managed-by: bob-quality` (CT5).
  9. `versão`/`download`: URLs padrão = `DEFAULT_API`/`DEFAULT_DOWNLOAD`; opções do `curl` = `CURL_OPTS`; `pip` com `PIP_OPTS`.
  10. nenhum bloco contém `install.sh` nem `sudo`; cada bloco passa em `sh -n` (e em `dash -n` se existir).
  11. `BOB_VERSION`: só o bloco `versão` a cita, e só como leitura `${BOB_VERSION:-}`/`$BOB_VERSION`; nenhum bloco a atribui ou exporta (regex `(^|[;\s])(export\s+)?BOB_VERSION=`); nenhuma mensagem `fail` cita `BOB_VERSION`; fora dos blocos, ela aparece só na linha da nota que começa com `> Somente testes/release-check:` (pt-BR) ou `> Tests/release-check only:` (en), uma vez; a seção `Regras` não a cita. Mesmo teste no `install.sh`: `--help` e as mensagens de erro não citam `BOB_VERSION` exceto a de valor inválido.

**Prova.**
- Automática: o teste acima (U8, `pytest`) e o passo 14 do harness, **proposto** (CT15).
- Manual por release (CT13, tabela "Prompt de IA"): um agente de IA real recebe o arquivo do prompt num projeto novo e segue os passos; evidência = saída de `setup` e `verificação`, e a confirmação de que o agente não baixou `install.sh`.

**Dona.** U8 confirmada. U8 depende de U1–U7 e consome CT2, CT3, CT5, CT6 (U1), CT8 (U2), CT9 (U3), CT12, CT14, CT15 (U1) e CT16 (U6): todos de units das quais já depende. Consumidora: U9 (roda o harness completo e o release-check). Nenhuma aresta nova.

## CT15 — Harness `scripts/verify-install.sh` (v1.1)
- Dona U1 (2.7: infraestrutura compartilhada). Cada unit acrescenta os seus passos (`unit-of-work.md`).
- Sintaxe: `sh scripts/verify-install.sh [--only <n>[,<n>...]]`. `--only` roda só os passos pedidos (para a ET de cada unit); sem ele, todos os que existem.
- Saída: `0` se todos os passos rodados passam; `1` no primeiro que falha, com stderr `verify-install: passo <n>: <motivo>`. Uso inválido: `1`.
- Modo espelho (padrão): `python -m build --wheel`, copia `scripts/install.sh`, gera `SHA256SUMS` (CT12), serve `<tmp>/mirror` em `http://127.0.0.1:<porta livre>` com o layout `api/releases/latest` + `download/<tag>/<asset>`, exporta `BOB_RELEASES_URL`. Pré-release e rascunho do espelho ficam fora de `api/releases/latest`.
- `VERIFY_REMOTE=1`: sem espelho; usa o GitHub (CT14).
- `VERIFY_DIST=<dir>` (ADR 0030, v1.1): quando não vazio, `build_wheel()` usa `$VERIFY_DIST/bob_quality-$X-py3-none-any.whl` (copiado para `$T/dist/`) em vez de construir um wheel novo; se o arquivo não existir, falha no preparo com `verify-install: preparo: VERIFY_DIST sem bob_quality-$X-py3-none-any.whl` e código `1`.
- Cada passo: `HOME` temporário novo, `PATH=/usr/bin:/bin:<dir do node>:<dir do python3>`, `BOB_HOME` dentro do `HOME`.
- Fixture de gitleaks (até o U3): põe `gitleaks` 8.30.1 num diretório do `PATH`; o harness baixa e confere pelo CT9.
- Passos: os de `verification-command.md` (2.6) mais os acréscimos das units. Depois da U6 e da U7: `STEP_IDS='1 2 3 4 5 6 7 8 9a 9b 10 11 12 13'` (ADR 0026). Depois da U8 T4: `… 13 14`.
- **Passos 10 e 11 (U7, ADR 0026).** `ensure_8` / `ensure_10`; espelho `$T/mirror/upd/` com wheel rebatizado `X.Y.(Z+1)`; `run_bob`; passo 2 confere `bob --version` no modo espelho; `VERIFY_REMOTE=1` → "não se aplica"; alvos ≤ 300 s (passo 10) e ≤ 30 s (passo 11).
- **Passo 13 (U6, ADR 0026).** 5 casos de perfil; `run_oneliner` com `${10}`=`SHELL` e `${11}`=`BOB_HOME`; root → `die_passo 13`; alvo ≤ 180 s.
- **Passo 14 (U8, ADR 0028/0029): prompt de IA sem `install.sh` (CT18).** Unit: U8 acrescenta; U9 roda no harness completo.
  1. Espelho local (modo padrão) com wheel, `SHA256SUMS` e o tar.gz do gitleaks da plataforma; exporta `BOB_RELEASES_URL` e `BOB_GITLEAKS_BASE_URL`. `npm_config_cache=$T/npm-cache` (fora do `HOME`). Variáveis de proxy/índice via `pass_env` (ADR 0028).
  2. Instalação A: `HOME` novo, projeto fixture, `PATH` do harness, **sem** `SHELL` (perfil em `~/.profile`, como no `run_oneliner` de 9 args). Roda o comando único (`run_oneliner`). Grava o manifesto A (`manifest` / `install_state`).
  3. Apaga `HOME` e projeto e recria do zero nos **mesmos caminhos**.
  4. Instalação B: `prompt_blocks` extrai os blocos de `docs/install-prompt.en.md` (regex do CT18), filtra por `box_platform`, grava 14 arquivos e roda cada um num `sh` separado (`run_blocks` / `env -i`). Para no primeiro ≠ 0. Pedidos ao espelho = exatamente API + wheel + SHA256SUMS + gitleaks (0 de `install.sh`). `sudo.log` vazio. Grava o manifesto B.
  5. Manifesto = linhas ordenadas `rótulo TAB tipo TAB modo TAB extra` de: `$BOB_HOME` sem o conteúdo de `versions/*/venv/` (no lugar: 1 linha `freeze` com sha256 do `pip freeze --all` normalizado — `bob-quality @ …` vira `bob-quality @ <wheel>`); `~/.local/bin/bob`; `~/.profile`; `.agents/skills/**`; `bob.yaml`; `.git/hooks/pre-push`. Mais: código do `bob doctor` e as 2 linhas de `bob --version`.
  6. Passa se A = B. Depois roda os blocos de novo (B2): `~/.profile` com o mesmo sha256, `bob-prompt: pacote: ok (reused)` e `bob-prompt: gitleaks: ok (reused)` 1 vez cada, linha final do `verificação`. Alvo ≤ 360 s. `VERIFY_REMOTE=1` → "não se aplica".
  - Saída: `verify-install: passo 14: <primeira diferença ou bloco que falhou>`.

---

## Propostas ao Analista (FR/US)
> Superadas pelo Adendo A1 do Analista (`requirements.md`: FR1.6, FR1.7, FR1.8, FR8.4, FR8.5, NFR10, NFR11; `stories.md`: US1.5). A rastreabilidade usa os IDs reais (`contract-traceability.md`). O texto abaixo fica como histórico.

Origem: Emerson, via Maestro, 18/10/2026 19:14 (UTC-3), literal: (1) "Adicione um prompt que orie te um modelo de IA a como instalar passo a passo o pacote sem depender de um arquivo .sh"; (2) "Deve haver as duas opções a principal sendo o arquivo .sh". Não editei `requirements.md` nem `stories.md`; o Analista decide o texto final.
- **FR1.6 (proposto):** além do comando único (caminho principal), há um caminho alternativo: um prompt que guia um agente de IA a instalar o bob passo a passo, **sem depender do `install.sh`** (não baixa nem executa o script), com **o mesmo resultado** (mesmos caminhos, marcadores, launcher e versões). Em divergência, vale o comando único.
- **FR8.4 (proposto):** os docs de instalação mostram primeiro o comando único e depois, como alternativa, o prompt para agente de IA. Origem: fala (2), FR8.1.
- **US1.5 (proposta):** Como Dev, quero pedir ao meu agente de IA para instalar o bob passo a passo, para instalar sem rodar o script.
  1. Dado um projeto novo e o prompt dos docs colado no meu agente, quando o agente termina, então o resultado é o mesmo do comando único: `bob doctor` = 0, `bob --version` = versão alvo, skills só em `.agents/skills`, `bob.yaml`, hook e linha do perfil.
  2. Dado o prompt, quando o agente o segue, então ele **não baixa nem executa `install.sh`** e não usa `sudo`.
  3. Dado que um passo falha (inclusive sha256), quando o agente para, então ele me mostra a saída do passo, sem contornar.
  4. Dado os docs de instalação, quando os leio, então o comando único aparece antes do prompt, e o prompt está marcado como alternativa.
  - Cobre: FR1.6, FR8.4. Unit: U8 (CT17, CT18); prova: `pytest` (paridade), passo 14 proposto (CT15), manual por release (CT13).
- Impacto em units: nenhuma unit nova; U8 ganha os 2 arquivos de prompt, o teste de paridade e o passo 14; U1 declara as 6 fontes únicas no topo do `install.sh` (CT2); U9 ganha a linha do release-check. Sem aresta nova no DAG.
- **Proposta ao Maestro:** acrescentar o passo 14 ao Comando de Verificação (`verification-command.md`, 2.6) e à lista de passos de U8/U9 (`unit-of-work.md`, 2.7). Não editei esses estágios.

## Inconsistências encontradas
Registradas aqui; os estágios aprovados não foram editados.

| # | Onde | Achado | Resolução neste contrato |
|---|---|---|---|
| I1 | 2.6 `components.md` C09 ("função nova `node_range()`") × repo | Já existe `node_range(pin: NodePin) -> str` em `doctor.py:250-251`, usada na mensagem do Node. | CT8: a nova é `npm_tools.node_range() -> NodeRange`; a do doctor fica. Nomes iguais em módulos diferentes, assinaturas diferentes. |
| I2 | 2.6 ADR 0017 / C03 ("pasta sem `.bob-version` fica") × repo | Hoje `_install` apaga e recopia a pasta da skill sem olhar posse (`install_skills.py:195-197`). Instalações antigas do bob (sem `.bob-version`) passariam a ser "alheias" e ficariam velhas. | CT4 regra 3: preserva e avisa com a ação ("apague a pasta e rode bob setup de novo"). Sem adivinhar posse. O CLI `install_skills` mantém o comportamento atual (sobrescreve), porque é o uso manual existente. |
| I3 | 2.6 C10 / ADR 0018 ("compara com a versão instalada") × FR6.5 ("Se o **projeto** já está na release mais nova") | Comparar só o pacote faz um segundo projeto, com skills velhas, ouvir "já está na mais nova". O venv é por usuário, as skills são por projeto. | CT11: compara pacote **e** `.bob-version` do projeto. Pacote novo + projeto velho → roda `bob setup`, sem download. |
| I4 | 2.6 `component-interfaces.md` §1 (passos do `install.sh`) | Não confere `git`/raiz do projeto nem `npm`/`curl`/`sha256sum` antes de instalar; a falha só viria no `bob setup`, depois do venv. Fere o espírito de US1.2 crit. 1. | CT2: passos `projeto` e `ferramentas` antes de qualquer escrita; `node` também confere `npm`. |
| I5 | 2.6 C08 ("Binários: primeiro `BOB_HOME/bin`") × `_locate` atual | `_locate` olha `cwd/node_modules/.bin` antes do `PATH` para **qualquer** executável, inclusive `node` e `gitleaks` (`doctor.py:437-441`). | CT8: U2 tira o `cwd` de `_locate`; U3 põe `BOB_HOME/bin` antes do `PATH`. |
| I6 | Mensagens do `install_skills` × idioma padrão `en` | Texto fixo em pt-BR (`install_skills.py:100`, `:182`, `:190`, `:193`), enquanto o bob usa `en` por padrão (`messages.py:10`). | CT4: o CLI manual fica como está; o `bob setup` usa `install_project_skills` e renderiza pelo catálogo (CT1). |

| I7 | 2.7 `unit-of-work.md` U2 ("Passos: `pytest`; 8 (parcial)") × DAG | O passo 8 roda no harness `verify-install.sh`, que é do U1; o U1 depende do U2, não o contrário. O U2 não pode ser provado por um passo do harness. | CT8 e `contract-traceability.md`: o pronto 4 do U2 (vitest do projeto, doctor `0`) é provado por teste `pytest` (doctor rodado num `cwd` temporário com `node_modules/vitest` 4.x). O passo 8 reprova isso depois, como parte do U1. U2 fora das consumidoras de CT1, CT6 e CT15. |
| I8 | 2.6 `component-interfaces.md` §1 (linha `versão`) e `decisions.md` (ADR 0011, "ação 'tente de novo ou defina `BOB_VERSION`'") × FR1.4 | A mensagem oferece `BOB_VERSION` ao dev como saída para falha da API; o uso normal é sempre a última publicada e `BOB_VERSION` é só para testes/release-check. | CT2/CT14/CT18: mensagem vira "tente de novo mais tarde"; CT6 diz quem escreve `BOB_VERSION`. Esclarecimento compatível da v1. 2.6 não editado. |

Verificado em 2026-10-22 (U4, `main` @ `b142631`): `include: ["."]` rodando os gates (ADR 0015). Passo 0 e e2e da T2 (PR #196: `include: ["."]`, `bob check` `EXIT:0`); `tests/test_check_report.py::test_a_repo_without_code_skips_crap_and_coverage_and_exits_0` (T1b, PR #197); passo 5 do `scripts/verify-install.sh`, caso `sem-codigo` (T3, PR #198), verde no `verify-install / linux-x64` da `main` `b142631`. Não verificado (fica para o 3.6): `tests/test_hook.py` com o template novo; rótulos de runner (3.7).

## Registro
- 2026-10-18 (UTC-3): CT1–CT17 criados em `v1`.
- 2026-10-18 19:15 (UTC-3): CT18 criado em `v1`; CT17 e CT13 (modelo do release-check) ganham a ordem principal/alternativa e a verificação do prompt. Origem: Emerson, via Maestro, 18/10/2026 19:14 UTC-3: "Deve haver as duas opções a principal sendo o arquivo .sh". Mudança compatível (só acréscimo).
- 2026-10-18 19:43 (UTC-3): origem das duas falas corrigida para 19:14 (ambas). `BOB_VERSION` esclarecido como só testes/release-check/`bob update` em CT2, CT6, CT14, CT17 e CT18 (nota no prompt, item 11 da paridade, mensagem de falha sem `BOB_VERSION`); I8 registrada. Esclarecimento compatível da v1.
- 2026-10-18 19:17 (UTC-3): CT18 refeito (ainda `v1`, não estava aprovado): prompt sem `install.sh`, 14 passos com comando exato por plataforma, tabela de equivalência, paridade com fontes únicas e passo 14 proposto. CT2 ganha 6 fontes únicas no topo do script (acréscimo compatível). CT17: o doc traz link para o prompt (não o texto inteiro); ordem mantida. CT6, CT12, CT14 e CT15 ganham U8 como consumidora. Origem: Emerson, via Maestro, 18/10/2026 19:14 (UTC-3), literal: (1) "Adicione um prompt que orie te um modelo de IA a como instalar passo a passo o pacote sem depender de um arquivo .sh"; (2) "Deve haver as duas opções a principal sendo o arquivo .sh".
- 2026-10-19 23:1x (UTC-3): CT14 (só texto; continua `v1`): retry no limite de taxa esclarecido. `install.sh`/`curl` (`CURL_OPTS` com `--retry 2`): `429` pode ser repetido até 2 vezes, `403` nunca. Python (`gitleaks.py`, `bob update`): `4xx`, inclusive `429`, sem retry. Código, saídas e mensagens sem mudança (o `install.sh` já fazia isso desde o #188). Resolve a I15 (U1/U3). Origem: Q1 = A da U3, Emerson, via Maestro, 19/10/2026 23:10 (UTC-3), literal: "Q1 A, Q2 A." Mudança compatível.
- 2026-10-22 (UTC-3): CT7 sobe de `v1` para `v2` pela emenda E2 (T1b). O que muda: sem código a medir no `paths.include`, `crap` e `coverage` ficam `not_run` com o motivo "no code to measure" e contribuem `0` (antes saíam `4`); com código, falha do coverage segue `4`. Texto, regra de `include` e estados do `bob.yaml` não mudam. Aprovação: Emerson, 2026-10-20 21:42 UTC-3 ("Aprovo a T1b e as emendas E1 a E3, com a T1c separada para a E4."). Entregue na T1b (PR #197, `637ec39`) e documentado na T1c (PR #199, `b142631`). Não há `v1` a manter: as consumidoras (U8, U9) ainda não começaram.
- 2026-10-22 (UTC-3): CT10 continua `v1`; acréscimos compatíveis do plano da U5 (`construction/u5-hook-pre-push/`), sem mudar nome, estado nem template: constante `HOOK_MARKER`, `HookPathError(ValueError)` (caminho do launcher não absoluto ou com `"`, `$`, `` ` ``, `\`, quebra de linha), `render_hook(bob_bin) -> bytes` e campo `HookResult.hooks_path: str = ""` (valor cru de `core.hooksPath`). Link e pasta no lugar de `pre-push` → `preserved` sem leitura; mesmo conteúdo com modo ≠ `0755` → `updated`. Os avisos do CT10 entram no catálogo (CT1) em en e pt-BR, com o texto pt sem o prefixo `hook: aviso:`, que vem de `setup.warning_line`. Erros do git: chave nova `git.command_failed`. Consumidoras (U8, U9) ainda não começaram. Registro no complemento da ADR 0016 e em `construction/u5-hook-pre-push/trace.md` (I35–I44).
- 2026-10-22 22:17 (UTC-3): Plan Approval Emerson (via Maestro). CT6 e CT16 sobem para `v2` (ADR 0021, 0022; sem v1 a manter). Acréscimos/esclarecimentos compatíveis: CT2 (linha `setup`), CT3 (resumo `already-marked:<arquivo>` + textos en), CT4 (`manifest_skill_names`), CT8 e CT11 (`mixed (…, not installed)`, Q1 = A; `--version` por `Action`), CT15 (passos 10, 11, 13 e forma do passo 14), CT17 (8 arquivos, bloco de shell, `## Update`, links ADR 0028), CT18 (bloco `perfil`: `already-marked:$F` e `S=${SHELL:-}`). ADRs 0021–0029 promovidas para `application-design/decisions.md`.
- 2026-10-24 12:41 (UTC-3): Plan Approval da U9 pelo Emerson (via Maestro). CT15 sobe para `v1.1` (adição compatível, ADR 0030): `VERIFY_DIST` em `build_wheel()` para o job `verify` do `release.yml` testar o wheel construído no job `check`. ADR 0030 promovida para `application-design/decisions.md`. U9 Q1 = B (ADRs 0008–0029 em `docs/adr/`), U9 Q2 = A (Emerson dispara ou autoriza o `dry_run` após os merges).
