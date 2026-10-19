# 2.6 Application Design — Interfaces e comandos

Projeto: bob. Profundidade: Minimal. Data: 2026-10-18 (UTC-3).
Códigos de saída seguem a ADR 0003 do repo: `0` sucesso; `4` configuração ou ferramenta. Os comandos novos só usam `0` e `4`.
Idioma das mensagens: `en` por padrão; `pt-BR` por `--lang` ou `BOB_LANG` (R-S7). Abaixo, o texto em pt-BR; o en tem o mesmo conteúdo.
Formato padrão de erro (FR7.2, NFR9), sempre no stderr:
```
bob setup: <passo>: <o que falhou>. <ação a tomar>.
```

## 1. Comando único de instalação (C01)
```sh
curl -fsSL https://github.com/fazedordecodigo/bob/releases/latest/download/install.sh | sh
```
- Roda na raiz do projeto (git). Argumentos opcionais: `sh -s -- --lang pt-BR`.
- Variáveis: `BOB_VERSION` (tag `vX.Y.Z`; padrão: última release publicada), `BOB_HOME`, `BOB_LANG`, `BOB_RELEASES_URL` (base de API e download; testes e espelho).
- Entradas: rede (GitHub, PyPI, npm; R-S5), `python3`, `node`, `git`.
- Saídas: `BOB_HOME/versions/<v>/venv`, `BOB_HOME/current`, `BOB_HOME/bin/bob`, `~/.local/bin/bob`; se preciso, uma linha no perfil do shell (passo `perfil`); depois as saídas do `bob setup`.

| Passo | Confere | Erro (pt-BR) |
|---|---|---|
| plataforma | `uname -s` em Linux/Darwin; `uname -m` em `x86_64`/`aarch64`/`arm64` | `install: plataforma: <so>/<arch> não é suportada. Suportadas: Linux e macOS, x64 e arm64.` |
| python | `python3` ≥ 3.10 e `python3 -m venv` disponível | `install: python: encontrado <v>, exigido >=3.10. Instale um Python 3.10 ou mais novo.` / `install: python: o módulo venv não está disponível. No Ubuntu, instale o pacote python3-venv.` |
| node | `node` em `>=22.18.0 <23`, sem sufixo | `install: node: encontrado <v>, exigido >=22.18.0 <23. Instale o Node 22.18.0 ou mais novo da linha 22.` |
| versão | API `releases/latest` ou `BOB_VERSION` | `install: versão: não consegui ler a última release (<status>). Tente de novo ou defina BOB_VERSION.` |
| download | wheel e `SHA256SUMS` da tag | `install: download: <url> falhou (<status>). Confira a rede e tente de novo.` |
| integridade | sha256 do wheel = `SHA256SUMS` | `install: integridade: o sha256 de <arquivo> não confere. Nada foi instalado. Tente de novo.` |
| pacote | `python3 -m venv` + `pip install <wheel>` | `install: pacote: pip falhou. Veja a saída acima e tente de novo.` |
| perfil | só se `~/.local/bin` não está no `PATH`; arquivo por `$SHELL`: `zsh` → `${ZDOTDIR:-$HOME}/.zshrc`, `bash` → `~/.bashrc`, outro ou vazio → `~/.profile`; já tem `# managed-by: bob-quality` → nada; não existe → cria só com a linha | aviso, não erro: `install: perfil: não consegui gravar <arquivo> (<erro>). Para usar o comando bob, acrescente ao seu perfil: export PATH="$HOME/.local/bin:$PATH"` |

- Código de saída: `0` se tudo passa e o `bob setup` sai `0`; senão `4` (ou o código do `bob setup`). O passo `perfil` nunca muda o código.
- Linha gravada no perfil (sempre igual):
```sh
export PATH="$HOME/.local/bin:$PATH" # managed-by: bob-quality
```
- O resultado do passo `perfil` vai para o `bob setup` em `BOB_INSTALL_PROFILE` (`<arquivo>`, `already-on-path`, `already-marked`, `failed:<arquivo>`). Variável interna; não documentada para o dev.
- Falha em qualquer passo acima: 0 arquivos do projeto alterados.

## 2. `bob setup` (C02)
```
bob setup [--lang en|pt-BR]
```
- Sem `--config` (como `doctor`). Projeto = pasta atual.
- Saída padrão: uma linha por passo e o resumo final (FR7.1):
```
bob setup: resumo
  instalado: ferramentas npm, gitleaks 8.30.1, skills (bob-check, harden, review-report) em .agents/skills, bob.yaml, hook pre-push
  preservado: <item> (<motivo>)
  avisos: <aviso>
  perfil do shell: <linha abaixo>
  bob doctor: 0
```
- Linha `perfil do shell` (só quando o `bob setup` veio do `install.sh`):
  - `<arquivo>`: `acrescentei ~/.local/bin ao PATH em <arquivo>. Abra um terminal novo ou rode: . <arquivo>`
  - `already-on-path`: `~/.local/bin já está no PATH; nada mudou`
  - `already-marked`: `<arquivo> já tem a linha do bob; nada mudou`
  - `failed:<arquivo>`: `não consegui gravar <arquivo>; veja o aviso acima`

| Passo | Ação | Preserva/avisa | Erro (pt-BR) |
|---|---|---|---|
| projeto | `git rev-parse --show-toplevel` = pasta atual | — | `bob setup: projeto: <dir> não é a raiz de um repositório git. Rode na raiz do projeto.` |
| runtimes | Python e Node na faixa (C09) | — | igual ao `install.sh` |
| npm | `npm ci --prefix <pacote>` (fallback para cache, como hoje) | — | `bob setup: npm: npm ci falhou. <comando exato>` |
| gitleaks | C07 | já instalado: não baixa | `bob setup: gitleaks: o sha256 de <asset> não confere. Nada foi instalado. Tente de novo.` |
| skills | C03 alvo `agents` → `.agents/skills` | pasta sem `.bob-version` fica; cópia do bob em `.claude/skills` ou `.github/skills` gera aviso: `bob setup: skills: achei uma cópia do bob em <pasta>. O bob agora usa só .agents/skills; apague <pasta> se não precisar dela.` | `bob setup: skills: <motivo>. <ação>.` |
| bob.yaml | C05 | existe: preserva e avisa; sem código: aviso | `bob setup: bob.yaml: o arquivo gerado é inválido (<erro>). Abra uma issue.` |
| hook | C06 | hook alheio ou `core.hooksPath`: preserva e avisa | `bob setup: hook: não consegui gravar <caminho> (<erro>). Confira as permissões.` |
| doctor | `run_doctor()` | — | (a tabela do doctor) |

- Código de saída: o do `bob doctor` (`0` ou `4`). Falha num passo anterior: `4`.
- Não pergunta nada. Repetir dá `0` e altera 0 arquivos (NFR4).

## 3. Skills por agente (C03)
```
python -m bob_quality.install_skills [--project DIR] [--source DIR] {copilot,devin,agents}...
```
| Alvo | Pasta | Usado pelo `bob setup` |
|---|---|---|
| `agents` | `.agents/skills` | sim, único (ADR 0009) |
| `devin` | `.agents/skills` (mesma pasta) | não |
| `copilot` | `.github/skills` | não |

- Entrada: manifesto `<fonte>/.claude-plugin/plugin.json`. Fonte: `--source`, clone, ou `bob_quality/plugin/` (ADR 0010).
- Saída: `<pasta>/<skill>/` com `SKILL.md`, `LICENSE`, `.bob-version`. Linha `N skills em <pasta>`.
- Avisos no stderr: pasta alheia preservada; duplicata provável.
- Saída: `0`; manifesto ausente ou inválido: `4` (como hoje).

## 4. Geração do `bob.yaml` (C05)
- Função `write_default_config(project: Path) -> ConfigResult` (estado: `criado`, `preservado`, `criado_sem_codigo`).
- Texto gerado (exemplo, projeto com `src/`):
```yaml
base: origin/main
language: en
paths:
  include: [src]
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
- Avisos: `bob.yaml já existe; preservado sem mudanças.`; `nenhuma pasta de código encontrada; paths.include: ["."].`
- Regra de `paths.include`: ADR 0015.

## 5. Hook pre-push (C06)
- Função `install_hook(project: Path, bob_bin: Path) -> HookResult` (`criado`, `atualizado`, `inalterado`, `preservado`, `preservado_hookspath`).
- Template: ADR 0016.
- Avisos: `hook pre-push existente preservado (<caminho>). Para usar o do bob, acrescente: <bob_bin> check --gates crap,dry,deps`; `core.hooksPath=<valor>; hook não instalado. Acrescente ao seu gerenciador de hooks: <linha>`.

## 6. gitleaks (C07)
- Função `ensure_gitleaks(home: Path) -> Path`. Tabela e fluxo: ADR 0014.
- Variável: `BOB_GITLEAKS_BASE_URL` (padrão `https://github.com/gitleaks/gitleaks/releases/download/v8.30.1`).
- Erros: plataforma fora da tabela; download; integridade; extração (membro ausente ou com caminho). Todos `4`, nada instalado.

## 7. `bob doctor` (C08)
```
bob doctor [--install] [--lang en|pt-BR]
```
- Mesma saída de hoje: `<nome> expected <esperado> found <encontrado>` por ferramenta.
- Esperado npm e Node: do `package.json` empacotado (ADR 0008). gitleaks: da tabela (ADR 0014).
- Linha nova, informativa: `skills do projeto: <versão> (.agents/skills)` ou `skills do projeto: não instaladas`.
- `--install`: `npm ci` e gitleaks.
- Saída: `0` se todas batem; `4` se falta ou diverge (como hoje). Erro de leitura do `package.json`: `4`, `bob doctor: não consegui ler <caminho> (<erro>).`

## 8. `bob update` (C10)
```
bob update [--lang en|pt-BR]
```
- Entrada: API `releases/latest` (ou `BOB_RELEASES_URL`). Versão instalada do pacote.
- Saídas: `já está na release mais nova (vX.Y.Z).` e `0`, sem alterar nada; ou `atualizando de vA para vB` e o código do `install.sh`.
- Erros: leitura da release; download; integridade do `install.sh`. Todos `4`.

## 9. `bob --version` (C10)
```
bob --version
bob 0.2.0
skills do projeto: 0.2.0 (.agents/skills)
```
- Sem skills: `skills do projeto: não instaladas`. Sai `0`.
