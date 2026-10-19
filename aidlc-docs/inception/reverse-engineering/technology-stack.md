# 2.1 Reverse Engineering — Stack de tecnologia (instalação e configuração)

Repo: `fazedordecodigo/bob`, `main` @ `d2e26bd`. Evidência `arquivo:linha` nesse commit.

## Linguagens e runtimes
| Item | Versão | Onde está |
|---|---|---|
| Python | `>=3.10` | `pyproject.toml:10` |
| Python no CI | 3.10 e 3.12 | `README.pt-BR.md:334` (não li `ci.yml`: Não verificado no arquivo) |
| Python na Action | 3.12 | `.github/actions/bob/action.yml:39-41` |
| Node | `>=22.18.0 <23` | `package.json:5-7`, `package-lock.json:19-21`, `src/bob_quality/doctor.py:62`, `:243-251` |
| Node na Action | 22.18.0 | `.github/actions/bob/action.yml:43-45` |
| Node no workflow `package` | 22.18.0 | `.github/workflows/package.yml:21-23` |
| Shell do hook | `/bin/sh` | `src/bob_quality/hooks/pre-push:1` |
| JS empacotado | `.mjs` em `src/bob_quality/js/` | `pyproject.toml:43` |

## Gerenciadores e build
- pip + setuptools (`pyproject.toml:1-3`). Sem lockfile Python. Dependências com `==` no próprio `pyproject.toml`.
- npm com `package-lock.json` v3 (`package-lock.json:3`). Instalação por `npm ci` (`src/bob_quality/npm_tools.py:165-170`).
- `uv==0.13.0`: instalado pela Action (`.github/actions/bob/install.sh:18`). O gate de security chama `uvx --from semgrep==1.180.0` (`docs/getting-started/installation.md:26`). `bob doctor` não confere `uv` nem `semgrep` (`src/bob_quality/doctor.py:64-112`).
- Build: `python -m build` e `twine check --strict` no workflow `package` (`.github/workflows/package.yml:41-45`). Não publica (`:47`).

## Ferramentas Python pinadas
Fonte de verdade: `pyproject.toml:13-25`. O doctor lê esses `==` do metadata do pacote (`src/bob_quality/doctor.py:143`, `:160-164`).

| Pacote | Versão | `pyproject.toml` | No doctor | README `:70` | `docs/instalacao.md:24` | `docs/getting-started/installation.md:26` |
|---|---|---|---|---|---|---|
| lizard | 1.24.1 | `:14` | sim `:65` | sim | sim | sim |
| deptry | 0.25.1 | `:15` | sim `:66` | **não** | **não** | sim |
| coverage | 7.16.2 | `:16` | sim `:67` | sim | sim | sim |
| diff-cover | 10.6.0 | `:17` | sim `:83` | sim | sim | sim |
| PyYAML | 6.0.3 | `:18` | não | **não** | sim | sim |
| import-linter | 2.15 | `:19` | sim `:81` | sim | sim | sim |
| grimp | 3.17 | `:20` | sim `:82` | sim | sim | sim |
| mutmut | 3.8.0 | `:21` | sim `:79` | sim | sim | sim |
| complexipy | 8.0.1 | `:22` | sim `:80` | **não** | **não** | sim |
| bandit | 1.9.4 | `:23` | sim `:84` | **não** | sim | sim |
| vulture | 2.16 | `:24` | sim `:98` | **não** | sim | sim |

Extra `dev` (`pyproject.toml:28-34`): pytest 9.1.1, jsonschema 4.26.0, build 1.6.1, twine 7.0.0, tomli 2.5.0 (Python < 3.11).

## Ferramentas npm pinadas
Duas fontes: `package.json:8-18` (com `package-lock.json`) e a tupla `PINS` do doctor, com versões escritas no código (`src/bob_quality/doctor.py:69-111`).

| Pacote | `package.json` | lock (versão) | doctor | README `:70` | `docs/instalacao.md:35` | `docs/getting-started/installation.md:37` |
|---|---|---|---|---|---|---|
| c8 | 12.0.0 `:9` | 12.0.0 `:3231` | 12.0.0 `:69` | sim | sim | sim |
| dependency-cruiser | 18.6.0 `:10` | 18.6.0 `:3641` | 18.6.0 `:85-90` | sim | sim | sim |
| eslint | 9.39.5 `:11` | 9.39.5 `:4013` | 9.39.5 `:72` | **não** | **não** | sim |
| eslint-plugin-sonarjs | 2.0.4 `:12` | 2.0.4 `:4298` | 2.0.4 `:73-78` | **não** | **não** | sim |
| jscpd | 5.4.1 `:13` | 5.4.1 `:8195` | 5.4.1 `:71` | sim | sim | sim |
| knip | 6.41.0 `:14` | 6.41.0 `:8405` | 6.41.0 `:99` | **não** | **não** | sim |
| vitest | **5.0.5** `:15` | **5.0.5** `:10842` | **5.0.4** `:70` | sim (`5.0.4` na tabela `:170`) | sim, `5.0.4` | sim, `5.0.4` |
| @stryker-mutator/core | 10.0.0 `:16` | 10.0.0 `:2424` | 10.0.0 `:100-105` | **não** em `:70` (sim na tabela `:172`) | **não** | sim |
| @stryker-mutator/vitest-runner | 10.0.0 `:17` | 10.0.0 `:2516` | 10.0.0 `:106-111` | **não** em `:70` (sim na tabela `:172`) | **não** | sim |

Colunas README: `README.pt-BR.md:70` e `README.md:70` têm a mesma lista.

## Binários fora de pip e npm
| Ferramenta | Versão | Onde | Observação |
|---|---|---|---|
| gitleaks | 8.30.1 | `src/bob_quality/doctor.py:91-97` | URL e sha256 só de `linux_x64` (`:95-96`). O workflow `package` instala à mão (`.github/workflows/package.yml:31-39`). Nenhuma menção em `README.pt-BR.md`, `README.md`, `docs/instalacao.md` nem `docs/getting-started/installation.md`. |
| semgrep | 1.180.0 | `docs/getting-started/installation.md:26` | Via `uvx`. Fora do doctor. |

## Divergências
1. **vitest: doctor 5.0.4 vs. `package.json` e lock 5.0.5.** Commit `d2e26bd` "chore(deps): bump vitest (#180)", 2026-10-18 16:39 UTC-3. O workflow `package` falhou nesse commit no passo `bob doctor`, com `vitest expected 5.0.4 found 5.0.5` e exit `4` (run 39159800688, job 117770515138, 16:41 UTC-3). Hoje, `bob doctor` sai `4` depois de um `npm ci` limpo.
2. **Node da Action.** `docs/getting-started/installation.md:15` diz que a Action ainda instala Node `22.14.0`. A Action instala `22.18.0` (`.github/actions/bob/action.yml:45`). `docs/instalacao.md:127` e `README.pt-BR.md:338` dizem `22.18.0`. A faixa de requisito bate em todos (`docs/getting-started/installation.md:10`, `docs/instalacao.md:10`, `README.pt-BR.md:62`).
3. **Lista de pinadas no README incompleta.** `README.pt-BR.md:70` e `README.md:70`: faltam deptry, complexipy, bandit, vulture e PyYAML (Python), e eslint, eslint-plugin-sonarjs, knip e os dois do Stryker (npm).
4. **`docs/instalacao.md` (pt-BR) atrás de `docs/getting-started/installation.md` (en).** Faltam deptry e complexipy em `:24` e as cinco npm mais novas em `:35`.
5. **vitest 5.0.4 nos docs.** `README.pt-BR.md:170`, `README.md:170`, `docs/instalacao.md:35`, `docs/getting-started/installation.md:37`. O pin real é 5.0.5.
6. **Inputs da Action no README.** `README.pt-BR.md:340` lista `base`, `gates`, `pip-spec`, `token`. Falta `language` (`.github/actions/bob/action.yml:29-34`). `docs/instalacao.md:123` já tem.
7. **gitleaks fora dos requisitos.** O doctor exige gitleaks (`src/bob_quality/doctor.py:91-97`). Os requisitos em `docs/instalacao.md:7-11` e `docs/getting-started/installation.md:7-11` não o citam.
