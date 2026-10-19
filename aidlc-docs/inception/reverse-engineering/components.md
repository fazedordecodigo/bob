# 2.1 Reverse Engineering — Componentes (instalação e configuração)

Repo: `fazedordecodigo/bob`, `main` @ `d2e26bd`. Evidência `arquivo:linha` nesse commit.

## 1. Pacote pip — `pyproject.toml`
- Responsabilidade: empacotar `bob-quality` e expor o comando `bob`.
- Nome `bob-quality`, versão `0.1.0` (`pyproject.toml:6-7`). Python `>=3.10` (`:10`).
- Script `bob = "bob_quality.cli:main"` (`:36-37`).
- Backend `setuptools>=68` (`:1-3`). Pacotes em `src/` (`:39-40`).
- Dados empacotados: `schemas/*.json`, `hooks/*`, `package.json`, `package-lock.json`, `js/*` (`:42-43`).
- Entrada: o código em `src/bob_quality`. Saída: sdist e wheel.
- Evidência do wheel real: o log do workflow `package` no commit `d2e26bd` adiciona `bob_quality/package.json`, `package-lock.json`, `hooks/pre-push`, `js/*.mjs` e `schemas/report_v1.json`. Nenhum arquivo de `skills/` nem `.claude-plugin/` (job 117770515138, run 39159800688, 2026-10-18 16:41 UTC-3).
- `src/bob_quality/package.json`, `package-lock.json` e `js/flush-coverage.mjs` são symlinks no git (modo `120000` na árvore de `main`).

## 2. CLI — `src/bob_quality/cli.py`
- Subcomandos: `check`, `crap`, `dry`, `deps`, `mutate`, `report`, `waive`, `doctor` (`src/bob_quality/cli.py:70-115`).
- `doctor` aceita `--install` (`:115-121`) e chama `run_doctor` (`:217-218`).
- Não existe subcomando de instalação, `init`, `setup` ou de skills.

## 3. Instalador de skills — `src/bob_quality/install_skills.py`
- Responsabilidade: copiar as skills listadas no manifesto para a pasta de skills de cada agente no projeto (`:1-4`).
- Roda como `python -m bob_quality.install_skills` ou direto do clone. Só usa a stdlib (`:1-4`).
- Entradas: `--project` (padrão `.`), `--source` (padrão `PLUGIN_ROOT`), um ou mais alvos (`:106-108`).
- `PLUGIN_ROOT = Path(__file__).resolve().parents[2]` (`:23`). Manifesto lido: `<source>/.claude-plugin/plugin.json` (`:24`, `:117`).
- Pastas de destino que ele conhece (`:17-21`):

| Alvo | Pasta no projeto | Agentes (comentário em `:15-16`) |
|---|---|---|
| `copilot` | `.github/skills` | Copilot |
| `devin` | `.agents/skills` | Devin |
| `agents` | `.agents/skills` | Cursor, Copilot, Devin e Codex |

- Não há alvo para Claude Code (`:17-21`; `docs/adr/0004-empacotamento-quatro-agentes.md:27`; `docs/getting-started/agents.md:38`).
- Saídas: uma pasta por skill, achatada pelo nome, com o `LICENSE` mais próximo (`:185-199`). Imprime `N skills em <pasta>` (`:98-100`).
- Reinstalar apaga e recopia só as skills do manifesto (`:194-197`). Remove pastas aposentadas só com o `NOTICE` antigo (`:172-183`).
- Pula destino que é symlink ou arquivo, com aviso (`:188-194`).
- Erro de manifesto: exit `4` (`:76`, `:85-89`). Mensagem pede `--source` (`:149`).
- Sem `--source`, num pacote instalado, o manifesto não existe e sai `4` (`docs/adr/0004-empacotamento-quatro-agentes.md:31`; `README.pt-BR.md:110`). Não testado por mim (Não verificado em execução).

## 4. Manifestos de plugin
- `.claude-plugin/plugin.json`: nome `bob`, versão `0.1.0`, `skills` = `./skills/bob-check`, `./skills/harden`, `./skills/review-report` (`.claude-plugin/plugin.json:2-3`, `:10-14`). É a fonte única da lista para o instalador (`docs/adr/0004-empacotamento-quatro-agentes.md:19`).
- `.claude-plugin/marketplace.json`: marketplace local `bob`, `source: ./`, "Ainda não publicado" (`.claude-plugin/marketplace.json:2`, `:4`, `:8`).
- `.cursor-plugin/plugin.json`: mesmo array de skills, mais `displayName` e `logo` (`.cursor-plugin/plugin.json:3`, `:10`, `:12-16`).
- Teste que trava os dois arrays iguais: `tests/test_packaging.py:136-139`.
- Skills no repo: `skills/bob-check/SKILL.md`, `skills/harden/SKILL.md`, `skills/review-report/SKILL.md` (árvore de `main`).

## 5. Configuração — `bob.yaml` e padrões
- Leitura: `load_config` usa `<cwd>/bob.yaml` ou `--config` (`src/bob_quality/config.py:311-317`).
- Sem `bob.yaml` e sem `--config`: usa `Config()` e detecta linguagens (`:313-316`, `:380-384`).
- Padrões da classe `Config` (`:275-297`): `base: origin/main`, `languages: (python,)`, `include: (src,)`, `exclude: tests, node_modules, dist` (`:15`), `max_crap: 10.0`, `crap_scope: changed`, `min_tokens: 50`, `new_clones: warn`, `max_new_clones: 0`, `coverage_min_percent: 80.0`, entre outros.
- Padrões documentados no README: `README.pt-BR.md:182-203`. Batem com a classe nas chaves listadas.
- Um `paths.include` que não existe no projeto sai `4` (`src/bob_quality/config.py:428-434`).
- `bob.yaml` do próprio repo: `base`, `languages: [python]`, `paths.include: [src]`, `exclude: [tests]`, `crap` (`bob.yaml:1-8`). Não é um modelo para outros projetos.
- Waivers: `.bob/waivers.yaml`, versionado (`README.pt-BR.md:236`).

## 6. Hook pre-push — `src/bob_quality/hooks/pre-push`
- Script `sh` de 5 linhas: `set -e`, limpa `PYTEST_ADDOPTS` e `PYTEST_PLUGINS`, `exec bob check --gates crap,dry,deps </dev/null` (`src/bob_quality/hooks/pre-push:1-5`).
- Chama `bob` pelo `PATH` (`:5`).
- Vai no wheel (`pyproject.toml:43`; log do build).
- Instalação: `cp` manual para `.git/hooks/pre-push` e `chmod +x` (`README.pt-BR.md:321-324`; `docs/guides/pre-push.md:7-10`).
- Teste: `tests/test_hook.py` confere < 60 s no fixture (`README.pt-BR.md:319`).

## 7. `bob doctor` — `src/bob_quality/doctor.py`
- Responsabilidade: listar versão esperada e encontrada de cada ferramenta e sair `0` ou `4` (`:1`, `:123-139`, `:175-178`).
- Python: compara com os `==` do próprio pacote, lidos de `importlib.metadata.requires` (`:143`, `:150-164`, `:228-240`).
- Node: aceita `>=22.18.0 <23`, só `X.Y.Z` sem sufixo (`:62`, `:243-261`).
- npm: versões fixas no código, não lidas do `package.json` (`:69-111`). Procura primeiro em `<cwd>/node_modules` (`:358-360`), depois no prefixo do pacote (`:363-368`), depois no executável no `PATH` (`:371-375`, `:437-441`).
- Binário: `gitleaks` 8.30.1, com URL `linux_x64` e sha256 (`:91-97`). Sem ele, exit `4`.
- `--install`: roda `npm ci` antes do relatório (`:129-133`; `src/bob_quality/npm_tools.py:133-142`). Não instala Python, Node nem gitleaks.

## 8. Ferramentas npm — `package.json` e `src/bob_quality/npm_tools.py`
- `package.json`: nome `bob-quality-tools`, privado, `engines.node >=22.18.0 <23`, 9 dependências exatas (`package.json:2-3`, `:5-7`, `:8-18`).
- `npm_prefix()`: acha o `package.json` do plugin subindo do arquivo do pacote. Prefere o cache do usuário se estiver igual (`src/bob_quality/npm_tools.py:63-80`, `:202-214`).
- Fallback de permissão: `EACCES`, `EPERM`, `EROFS` vão para o cache (`:16`, `:139-141`).

## 9. GitHub Action — `.github/actions/bob/`
- Fora do escopo do intent (Q3 C), mas é o único caminho sem clone que existe.
- Instala Python 3.12 e Node 22.18.0 (`.github/actions/bob/action.yml:39-45`).
- Resolve o requisito pip: `.[dev]` no repo do bob, ou `bob-quality[dev] @ git+https://github.com/<repo>.git@<ref>` (`.github/actions/bob/resolve_install.py:28-40`).
- Instala com pip e depois `uv==0.13.0` (`.github/actions/bob/install.sh:12-18`).

## 10. Docs de instalação
- `README.pt-BR.md`: instalação em `:60-110`, hook em `:317-324`. `README.md` é a versão em inglês (mesma estrutura; li só as linhas citadas).
- `docs/instalacao.md` (pt-BR) e `docs/getting-started/installation.md` (en).
- `docs/getting-started/agents.md` (en): alvos do instalador e plugin por agente.
- `docs/guides/pre-push.md` (en): hook.
- Divergências entre eles: ver `technology-stack.md`.
