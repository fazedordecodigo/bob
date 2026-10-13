# Instalação

[Índice](README.md) · [Visão geral](visao-geral.md) · [CLI](cli.md) · [Configuração](configuracao.md) · [Contribuição](contribuicao.md)

Há dois artefatos. O pacote pip `bob-quality` entrega o comando `bob`. O plugin `bob` entrega as skills aos agentes. Nada foi publicado no PyPI nem em marketplace: o [README.pt-BR.md](../README.pt-BR.md) e o comentário em `.github/workflows/package.yml` registram isso. Os passos abaixo partem de um clone de <https://github.com/fazedordecodigo/bob>, que é o que o código e os READMEs descrevem hoje.

## Requisitos

- Python 3.10 ou superior. O CI (`.github/workflows/ci.yml`) roda 3.10 e 3.12. `requires-python` em `pyproject.toml` é `>=3.10`.
- Node **22.14.0**. `bob doctor` compara a versão exata (`src/bob_quality/doctor.py`, pino `node` `22.14.0`). Outra versão, inclusive Node 20, faz o doctor sair com `4`.
- Para as ferramentas npm, `npm ci` na raiz do clone, ou `bob doctor --install` depois de instalar o pacote.

Num Ubuntu atual o Python do sistema recusa `pip install` pela PEP 668. Use um venv. Para o Node, `fnm install 22.14.0`, `nvm install 22.14.0`, ou o `.tar.gz` em <https://nodejs.org/dist/v22.14.0/>. O [AGENTS.md](../AGENTS.md) prefere o `.tar.gz` ao `.tar.xz` quando a imagem não tem `xz`.

## Pacote pip `bob-quality`

`pyproject.toml` declara o nome `bob-quality`, a versão `0.1.0` e o script:

```toml
[project.scripts]
bob = "bob_quality.cli:main"
```

As dependências Python pinadas no pacote são `lizard==1.24.1`, `coverage==7.16.2`, `PyYAML==6.0.3`, `import-linter==2.15`, `grimp==3.17` e `mutmut==3.8.0`. O extra `dev` traz `pytest`, `jsonschema`, `build` e `twine`.

Num checkout, para desenvolver:

```bash
python3 -m venv .venv && . .venv/bin/activate
python -m pip install -e '.[dev]'
npm ci
bob doctor
```

`pip install -e '.[dev]'` instala o comando `bob` e as ferramentas Python. `npm ci` instala, a partir do `package.json` da raiz (`name`: `bob-quality-tools`), `c8@12.0.0`, `vitest@5.0.3`, `jscpd@5.4.1` e `dependency-cruiser@18.5.0`. `bob doctor` lista cada ferramenta com a versão esperada e a encontrada e sai com `0` só quando todas coincidem.

O pacote instalado por pip carrega `package.json`, `package-lock.json` e `js/` (`tool.setuptools.package-data` em `pyproject.toml`). `bob doctor --install` roda `npm ci` nesse pacote. Se o npm falha com `EACCES`, `EPERM` ou `EROFS`, a instalação vai para `$XDG_CACHE_HOME/bob-quality` ou `~/.cache/bob-quality` (`src/bob_quality/npm_tools.py`). Outro erro do npm sai com `4` e o comando. Se o diretório do pacote não for gravável, a mensagem do doctor pede `bob doctor --install`.

O wheel não inclui as skills. Quem instalou só o pip e quer copiar skills para um projeto passa `--source` com o clone. Ver [Skills no projeto](#skills-no-projeto).

`bob doctor --install` num checkout editável cria `src/bob_quality/node_modules`. O [AGENTS.md](../AGENTS.md) registra que isso quebra `tests/test_mutmut_dogfood.py` ([#34](https://github.com/fazedordecodigo/bob/issues/34)). Apague essa pasta antes do `pytest`.

## Plugin nos agentes

Os manifestos são `.claude-plugin/plugin.json` (Claude Code; o Copilot CLI e o Devin também leem esse formato, segundo a [SPEC](SPEC.md)) e `.cursor-plugin/plugin.json` (Cursor). Os dois listam as mesmas skills:

- `./skills/bob-check`
- `./skills/harden`
- `./skills/review-report`

O marketplace local está em `.claude-plugin/marketplace.json`, nome `bob`, com a descrição de que ainda não foi publicado. Não há pasta `.plugin/`: a spec explica que o Copilot a leria antes de `.claude-plugin/`.

### Claude Code

O Claude Code lê `.claude-plugin/`. A partir do clone:

```bash
claude plugin marketplace add <caminho do clone>
claude plugin install bob@bob
```

Para uma sessão, `claude --plugin-dir <caminho do clone>`.

### Cursor

O Cursor lê `.cursor-plugin/`. A cópia precisa ser um diretório real, não um symlink, em `~/.cursor/plugins/local/bob`. Depois, **Developer: Reload Window**.

```bash
git clone <caminho do clone> ~/.cursor/plugins/local/bob
```

Skills achatadas dentro de um projeto ficam em `.agents/skills` (alvo `agents` do instalador). O plugin em `~/.cursor/plugins/local/bob` e as skills copiadas para o projeto são instalações diferentes: a primeira carrega o plugin; a segunda coloca `SKILL.md` na árvore do repositório.

### GitHub Copilot

O Copilot CLI lê `.claude-plugin/`, com os mesmos comandos do Claude Code:

```bash
copilot plugin marketplace add <caminho do clone>
copilot plugin install bob@bob
```

Skills no repositório, para o Copilot, vão para `.github/skills` (alvo `copilot`).

### Devin

A pasta recomendada na spec, com o link da doc do Devin, é `.agents/skills/<skill>/SKILL.md`. O instalador tem dois alvos que gravam nessa pasta ou na outra que o Devin também lê:

| Alvo | Pasta | Quem lê, segundo o README |
|---|---|---|
| `agents` | `.agents/skills` | Cursor, Copilot, Devin |
| `devin` | `.agents/skills` | Devin |
| `copilot` | `.github/skills` | Copilot e Devin |

O Devin lê as duas pastas. Instalar `copilot` e `devin` no mesmo projeto faz cada skill aparecer duas vezes. Escolha um alvo.

## Skills no projeto

`install_skills.py` lê a lista de skills de `.claude-plugin/plugin.json` e copia cada pasta, achatada pelo nome, com o `LICENSE` mais próximo entre a pasta da skill e a raiz do plugin. Não copia `NOTICE`.

```bash
python3 <caminho do clone>/src/bob_quality/install_skills.py --project <projeto> agents
```

O mesmo módulo roda como `python -m bob_quality.install_skills`. Com o pacote vindo do pip, passe `--source <caminho do clone>`, porque o wheel não traz as skills.

Sem manifesto, o instalador imprime o caminho que leu e sai com `4`. Se não houver `LICENSE` da pasta da skill até a raiz, avisa no stderr e ainda instala a skill.

Rodar de novo substitui as skills nomeadas no manifesto. Pastas de skills que o plugin deixou de distribuir (a lista `RETIRED_SKILL_NAMES` em `install_skills.py`, as 27 skills do Matt Pocock citadas no [CHANGELOG.md](../CHANGELOG.md)) só são apagadas quando o `NOTICE` é um arquivo regular com o texto que o instalador antigo gravava, do pin `49dd158d1076134a641b33efb035946536778336`. Um arquivo, um link simbólico, um `NOTICE` que é link simbólico, ou uma pasta sem esse texto, ficam, e o instalador avisa no stderr. Qualquer outra pasta fica.

## GitHub Action

A action composta `.github/actions/bob` instala o bob, roda `bob check` e comenta `.bob/report.md` num único comentário. Inputs, em `action.yml`:

| Input | Padrão | Efeito |
|---|---|---|
| `base` | vazio | Ref do diff. Vazio usa `origin/$GITHUB_BASE_REF` em pull request; senão o `bob.yaml` |
| `gates` | `crap,dry,deps,mutate` | Lista separada por vírgula |
| `pip-spec` | vazio | Requisito pip. Vazio instala o checkout quando ele é `bob-quality`; senão o git da action |
| `token` | vazio | Comentário e artefatos. Vazio usa `GITHUB_TOKEN` |
| `language` | vazio | `en` ou `pt-BR` para o check e o comentário. Vazio deixa `BOB_LANG` e `language` no `bob.yaml` |

Este repositório chama a action em `.github/workflows/bob.yml`. O `bob-quality` ainda não está no PyPI, então no checkout deste repositório a action usa `pip install -e ".[dev]"` (descrito no README; o script é `.github/actions/bob/install.sh`). Publicação no GitHub Marketplace está fora desta fatia, no README.

A action instala o Node `22.14.0` com `actions/setup-node` pinado por SHA e o jscpd `5.4.1` no prefixo npm do plugin (`install_jscpd.sh`, via `npm ci` do `bob doctor --install`). Sem isso, o gate dry fica `not_run` em repositórios que não instalam o Node. O artefato `bob-mutation-cache` fica 7 dias (`retention-days`) e leva `.bob/mutation-cache.json` e `.bob/stryker-incremental.json`.

## Hook pre-push

```bash
cp src/bob_quality/hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

O script executa `bob check --gates crap,dry,deps`. Ele segue `BOB_LANG` e `language` no `bob.yaml` porque esses dois entram na resolução de idioma da CLI. `tests/test_hook.py` confere que o hook termina em menos de 60 s no fixture, como o critério 7 da spec pede para `crap,dry,deps` no repo-fixture. Ver [o que cada superfície roda](cli.md#o-que-cada-superfície-roda).
