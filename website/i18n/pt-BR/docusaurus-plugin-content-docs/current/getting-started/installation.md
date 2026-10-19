# Instalação

[Índice](../README.md) · [Primeiro check](first-check.md) · [Agentes](agents.md) · [Contribuição](../contributing.md)

Há dois artefatos. O pacote pip `bob-quality` fornece o comando `bob`. O plugin `bob` fornece as skills aos agentes. Nada foi publicado no PyPI nem num marketplace. Os passos abaixo partem de um clone de <https://github.com/fazedordecodigo/bob>.

## Requisitos

- Python 3.10 ou mais novo. O CI (`.github/workflows/ci.yml`) roda 3.10 e 3.12. `requires-python` em `pyproject.toml` é `>=3.10`.
- Node `>=22.18.0 <23`. O `bob doctor` aceita essa faixa (`NODE` em `src/bob_quality/doctor.py`). O Node 20, o Node 24 e um sufixo `-rc` fazem o `doctor` sair com `4`. Um prerelease não casa com o padrão `X.Y.Z` que `_node_version` exige.
- Para as ferramentas npm, `npm ci` na raiz do clone, ou `bob doctor --install` depois que o pacote está instalado.

Num Ubuntu atual o Python do sistema recusa o `pip install` pela PEP 668. Use um venv. Para o Node, rode `fnm install 22.18.0` ou `nvm install 22.18.0`, ou baixe o `.tar.gz` de <https://nodejs.org/dist/v22.18.0/>. O [AGENTS.md](https://github.com/fazedordecodigo/bob/blob/main/AGENTS.md) prefere o `.tar.gz` ao `.tar.xz` quando a imagem não tem `xz`.

A GitHub Action composta instala o Node `22.18.0` (`.github/actions/bob/action.yml`). Esse pin é o passo de setup da Action. Está dentro da faixa que o `bob doctor` aceita. Ver [CI](../guides/ci.md).

## O pacote pip

`pyproject.toml` declara o nome `bob-quality`, a versão `0.1.0` e o script:

```toml
[project.scripts]
bob = "bob_quality.cli:main"
```

As dependências Python pinadas no pacote são `lizard==1.24.1`, `deptry==0.25.1`, `coverage==7.16.2`, `diff-cover==10.6.0`, `PyYAML==6.0.3`, `import-linter==2.15`, `grimp==3.17`, `mutmut==3.8.0`, `complexipy==8.0.1`, `bandit==1.9.4` e `vulture==2.16`. O extra `dev` traz `pytest==9.1.1`, `jsonschema==4.26.0`, `build==1.6.1` e `twine==7.0.0`. Em Python anterior a 3.11 o extra também pina `tomli==2.5.0`. O Semgrep 1.180.0 não é uma dependência. O gate de segurança roda `uvx --from semgrep==1.180.0`.

Num checkout, para desenvolvimento:

```bash
python3 -m venv .venv && . .venv/bin/activate
python -m pip install -e '.[dev]'
npm ci
bob doctor
```

`pip install -e '.[dev]'` instala o comando `bob` e as ferramentas Python. `npm ci` instala, a partir do `package.json` da raiz (`name`: `bob-quality-tools`), `c8@12.0.0`, `vitest@5.0.5`, `jscpd@5.4.1`, `dependency-cruiser@18.6.0`, `eslint@9.39.5`, `eslint-plugin-sonarjs@2.0.4`, `knip@6.41.0`, `@stryker-mutator/core@10.0.0` e `@stryker-mutator/vitest-runner@10.0.0`. O `bob doctor` lista cada ferramenta com a versão esperada e a versão encontrada e sai com `0` só quando todos os pins batem.

O pacote instalado pelo pip carrega `package.json`, `package-lock.json` e `js/` (`tool.setuptools.package-data` em `pyproject.toml`). `bob doctor --install` roda `npm ci` nesse pacote. Se o npm falha ali com `EACCES`, `EPERM` ou `EROFS`, a instalação vai para `$XDG_CACHE_HOME/bob-quality` ou `~/.cache/bob-quality` (`src/bob_quality/npm_tools.py`). Qualquer outro erro do npm sai com `4` e imprime o comando. Se o diretório do pacote não for gravável, a mensagem do doctor pede `bob doctor --install`.

O wheel não inclui as skills. A partir de uma instalação pip, passe `--source` com o clone. Ver [Agentes](agents.md).

Num checkout editável, `src/bob_quality/package.json` é um symlink para o `package.json` da raiz. `bob doctor --install` instala nessa raiz, no mesmo lugar que `npm ci`. Se `src/bob_quality/node_modules` já existe de um `--install` antigo, apague esse diretório antes do `pytest`. Ele quebra `tests/test_mutmut_dogfood.py`.

## A seguir

Rode o [primeiro check](first-check.md), ou instale as skills com [Agentes](agents.md).
