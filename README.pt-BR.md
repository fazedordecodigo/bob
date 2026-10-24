# bob

[English](README.md) | Português

O bob dá aos agentes de código (Cursor, Claude Code, GitHub Copilot, Devin) gates de qualidade determinísticos para o código que eles alteram, mais skills que dizem ao agente quando rodá-los. Os gates medem CRAP, duplicação, mutação e dependências, só nas funções do diff. Cada execução sai com um código que o agente consegue usar e grava um relatório de uma página que diz ao revisor humano onde olhar primeiro. Os gates seguem o fluxo do Uncle Bob (ver [Créditos](#créditos)).

- CLI: `bob` (`bob check | crap | dry | deps | mutate | report | waive | doctor | setup | update`)
- Pacote PyPI: `bob-quality` (sdist e wheel prontos, ainda não publicado)
- Nome nos marketplaces: `bob` (ainda não publicado)
- Configuração: `bob.yaml`
- Relatórios: `.bob/report.md` e `.bob/report.json` (schema v1)
- Idioma da saída: inglês (`en`, o padrão) ou português do Brasil (`pt-BR`)
- Documentação: [docs/README.md](docs/README.md) (guias em português; a spec continua em [docs/SPEC.md](docs/SPEC.md))

Licença: MIT.

## Status

Estas partes funcionam na `main`:

- CRAP em Python e TypeScript.
- Duplicação com jscpd, aviso por padrão e falha acima de um teto no modo fail.
- O gate de dependências, com a regra que proíbe ciclos.
- Mutação diferencial em Python e mutação incremental com Stryker em TypeScript, e `bob waive`.
- A GitHub Action que comenta o relatório no pull request.
- `bob doctor`, e o pacote `bob-quality` pronto para distribuir. Nada foi enviado ao PyPI.
- `bob report`, que renderiza um `report.json` já gravado como Markdown.
- Os manifestos de plugin para Claude Code, Cursor, Copilot e Devin, e o instalador de skills ([#10](https://github.com/fazedordecodigo/bob/issues/10)). Nada foi enviado a marketplace.

Estas partes estão planejadas (planned):

- Publicação no PyPI e nos marketplaces dos agentes.

## Fluxo

O agente altera o código. O hook pre-push roda os gates rápidos na máquina de quem desenvolve, e a GitHub Action roda os quatro gates no pull request. Os dois medem só as funções do diff, gravam o mesmo relatório e saem com os mesmos códigos.

```mermaid
flowchart TD
    agent["Agente altera o código"]
    agent --> hook["hook pre-push<br/>bob check --gates crap,dry,deps"]
    agent --> pr["Pull request"]
    pr --> action["GitHub Action<br/>bob check --gates crap,dry,deps,mutate"]
    hook --> diff["Os gates medem só as funções do diff"]
    action --> diff
    diff --> report[".bob/report.md<br/>.bob/report.json"]
    report --> code{"Exit code"}
    code -->|"0 passou"| done["O push ou o check do merge passa"]
    code -->|"1 gate falhou"| agent
    code -->|"2 testes da baseline falharam"| agent
    code -->|"3 sobrevivente sem waiver"| choice{"Matar ou registrar waiver?"}
    code -->|"4 config ou ferramenta"| doctor["bob doctor"]
    choice -->|"teste mais forte"| agent
    choice -->|"bob waive"| waivers[".bob/waivers.yaml"]
    waivers -->|"versionado com o código"| agent
    report --> comment["A Action cria ou atualiza um único comentário no PR"]
    comment --> human["O humano revisa o relatório e os waivers"]
```

## Instalar

Rode na raiz do seu projeto (um repositório git):

```bash
curl -fsSL https://github.com/fazedordecodigo/bob/releases/latest/download/install.sh | sh -s -- --lang pt-BR
```

Para mensagens em inglês, rode sem o `-s -- --lang pt-BR`.

O comando instala o bob em `BOB_HOME` (por padrão `~/.local/share/bob-quality`), liga o `bob` em `~/.local/bin` e põe essa pasta no `PATH` do perfil do seu shell. Depois roda o `bob setup` no projeto, que instala as ferramentas npm pinadas, o gitleaks `8.30.1`, as skills em `.agents/skills`, o `bob.yaml` e o hook de pre-push. Não usa `git clone`, plugin nem `sudo`.

Requisitos: Python 3.10 ou mais novo, Node `>=22.18.0 <23` com npm, git, curl e `sha256sum` ou `shasum`. Linux e macOS, em x64 e arm64.

### Alternativa: pedir ao seu agente de IA

Este caminho não usa o `install.sh`. Cole [o prompt para agente de IA](docs/install-prompt.pt-BR.md) no seu agente, na raiz do projeto; ele instala passo a passo e chega ao mesmo resultado. Se os dois caminhos divergirem, vale o comando único.

## Atualizar

```bash
bob update
bob --version
```

O `bob update` lê a última release. Se ela for mais nova que o seu bob, baixa o `install.sh` dela, confere o sha256 e o roda no projeto. Se só o projeto está atrasado, roda o `bob setup`. O `bob --version` mostra a versão do bob e a das skills do projeto.

## Instalação (desenvolvimento)

Você precisa de Python 3.10 ou superior e do Node 22.18.0, as versões que o CI usa. O Python do sistema de um Ubuntu atual recusa o `pip install` pela PEP 668, então instale dentro de um venv. Para ter o Node 22.18.0, rode `fnm install 22.18.0` ou `nvm install 22.18.0`, ou baixe o `.tar.gz` de <https://nodejs.org/dist/v22.18.0/>. Prefira o `.tar.gz` ao `.tar.xz`, porque a imagem pode não ter o `xz`.

```bash
python3 -m venv .venv && . .venv/bin/activate
python -m pip install -e ".[dev]"
npm ci
```

Esses comandos instalam o comando `bob`, as ferramentas Python pinadas em `pyproject.toml` (`lizard`, `coverage`, `diff-cover`, `mutmut`, `import-linter`, `grimp`) e as ferramentas npm pinadas em `package.json` (`c8`, `vitest`, `jscpd`, `dependency-cruiser`). `bob doctor` mostra a versão esperada e a encontrada de cada ferramenta.

## Instalação nos agentes

Nada foi publicado. Os comandos partem de um clone deste repositório. O plugin traz três skills, listadas em [Skills](#skills).

**Claude Code** lê `.claude-plugin/`. Adicione o clone como marketplace local e instale o plugin:

```bash
claude plugin marketplace add <caminho do clone>
claude plugin install bob@bob
```

Para uma sessão só, rode `claude --plugin-dir <caminho do clone>`.

**Cursor** lê `.cursor-plugin/`. Copie o clone para `~/.cursor/plugins/local/bob` como cópia real, não como symlink, e rode **Developer: Reload Window**:

```bash
git clone <caminho do clone> ~/.cursor/plugins/local/bob
```

**GitHub Copilot CLI** também lê `.claude-plugin/`:

```bash
copilot plugin marketplace add <caminho do clone>
copilot plugin install bob@bob
```

**Skills do repositório.** O `install_skills.py` copia as skills, achatadas, para a pasta de skills de um projeto:

```bash
python3 <caminho do clone>/src/bob_quality/install_skills.py --project <projeto> agents
```

| Alvo | Pasta | Lida por |
|---|---|---|
| `agents` | `.agents/skills` | Cursor, Copilot, Devin |
| `devin` | `.agents/skills` | Devin (a pasta recomendada por ele) |
| `copilot` | `.github/skills` | Copilot, Devin |

O Devin lê as duas pastas. Se um projeto receber `copilot` e `devin`, o Devin carrega cada skill duas vezes, então escolha um. Rodar o instalador de novo substitui as skills nomeadas no manifesto. Ele apaga uma pasta da lista fixa de skills que o plugin deixou de distribuir só quando o `NOTICE` dela é um arquivo regular com o texto gravado pela instalação antiga. Um arquivo, um link simbólico, um `NOTICE` que é link simbólico ou uma pasta sem esse texto ficam, e o instalador avisa no stderr. Qualquer outra pasta fica. Como o instalador achata as pastas, cada skill instalada leva uma cópia do `LICENSE` do plugin e não leva `NOTICE`. Ele também roda como `python -m bob_quality.install_skills`. O `bob-quality` instalado pelo pip não traz as skills, então passe `--source <caminho do clone>`. Sem manifesto, o instalador diz o caminho que leu e sai com `4`. Quando uma skill não tem `LICENSE` da pasta dela até a raiz do plugin, o instalador avisa no stderr e ainda assim a instala.

## Uso

Num repositório Python com `bob.yaml` e pytest:

```bash
bob check --base main
bob crap --base main
bob dry --base main
bob deps --base main
bob mutate --base main
bob waive <file::function|Target> --reason "texto de uma linha"
bob doctor
```

Cada comando aceita estas flags:

| Comando | Flags |
|---|---|
| `bob check` | `--base`, `--config`, `--out` (padrão `.bob/`), `--gates` (padrão `crap,dry,deps`), `--format` (`md`, `json` ou `both`, padrão `both`), `--dry-fail`, `--max-new-clones` |
| `bob crap` | `--base`, `--config`, `--out`, `--threshold`, `--coverage-file` |
| `bob dry` | `--base`, `--config`, `--out`, `--dry-fail`, `--max-new-clones` |
| `bob deps` | `--base`, `--config`, `--out` |
| `bob mutate` | `--base`, `--config`, `--out`, `--max-workers`, `--since-last-run` (reusa o cache, que já é o padrão) |
| `bob waive` | `arquivo::função` ou um Alvo do relatório de mutação, `--reason` |
| `bob doctor` | `--install` |

Todo comando aceita também `--lang en|pt-BR`, antes ou depois do nome do comando. Ver [Idioma da saída](#idioma-da-saída).

Os comandos gravam `.bob/report.md` e `.bob/report.json`. Os exit codes são:

| Código | Significado |
|---|---|
| `0` | Todo gate que rodou passou. |
| `1` | Um gate falhou. Uma função alterada tem CRAP no limite ou acima, o diff tem uma violação de dependência, ou, no modo fail do DRY, os clones novos passam de `duplication.max_new_clones`. |
| `2` | Os testes da baseline falharam antes de o bob medir. O gate `crap` também os roda no `bob check` padrão. |
| `3` | Um mutante sobrevivente não tem waiver. |
| `4` | Ferramenta ausente ou divergente, ou configuração inválida. A mensagem vai para o stderr em inglês, e a execução não grava nada. |

Um uso inválido da linha de comando sai com `4`, não grava relatório, e o stderr não menciona baseline. A ajuda (`-h`, `--help`) continua saindo com `0`.

`--config` antes do comando sai com `4` e não grava relatório. A última linha do stderr fica em inglês, mesmo com `--lang pt-BR`. Ela mostra o comando com a flag depois do nome, como em `bob: error: --config goes after the command: bob check --config ci.yaml`. Um caminho com espaço sai entre aspas, como em `bob crap --config 'my ci.yaml'`. `doctor` não aceita `--config`. A última linha é `bob: error: doctor does not accept --config`. `waive` também não aceita. A última linha é `bob: error: waive does not accept --config`. O `bob --help` não lista `--config`.

Quando mais de um gate falha, `bob check` sai com o código mais alto.

Um gate sem nada a medir não aumenta o exit code. Sem código sob `paths.include` (fora de `paths.exclude`), `crap` e `coverage` mostram ⏭️ `não executado (nenhum código a medir)`, e a execução pode sair com `0`.

`bob check` local não roda mutação. `bob check --gates mutate` e `bob mutate` rodam, só nas funções alteradas e nas funções que ainda têm sobreviventes.

## Como funciona

### Só o diff bloqueia

O bob roda `git diff <base>...HEAD` e mapeia as linhas alteradas para funções. Uma função conta como alterada quando o diff toca uma das linhas dela. Só funções alteradas, violações de dependência que tocam arquivos alterados e, no modo fail do DRY, clones que tocam linhas alteradas podem reprovar um gate. A dívida antiga vai para as seções informativas do relatório, marcada `fora do diff; não bloqueia`, e não muda o exit code. `--base` substitui a chave `base` do `bob.yaml`.

### Ferramentas pinadas por linguagem

O bob encapsula cada ferramenta num adaptador próprio e não copia código delas. As versões estão pinadas em `pyproject.toml` e `package.json`.

| Gate | Python | TypeScript |
|---|---|---|
| CRAP | `lizard` 1.24.1 para complexidade, `coverage` 7.16.2 rodando o pytest | `lizard` 1.24.1 para complexidade, `c8` 12.0.0 rodando o `vitest` 5.0.5 |
| Duplicação | `jscpd` 5.4.1 | `jscpd` 5.4.1 |
| Mutação | `mutmut` 3.8.0 | `@stryker-mutator/core` 10.0.0 e `@stryker-mutator/vitest-runner` 10.0.0 |
| Dependências | `import-linter` 2.15, `grimp` 3.17 | `dependency-cruiser` 18.6.0 |
| Cobertura do diff | `diff-cover` 10.6.0 sobre `coverage.xml` | `diff-cover` 10.6.0 sobre o lcov do c8 |

As ferramentas npm precisam do Node, e o jscpd precisa dele também num repositório só Python. Num repositório com Python e TypeScript, a falta do Node não é exit `4`. O bob continua medindo o Python e mostra o TypeScript como pulado, com aviso. O exit `4` continua quando a ferramenta ausente impede a medição pedida, como num repositório só TypeScript sem Node.

### `bob.yaml`

O bob lê estas chaves. Os valores abaixo valem quando a chave é omitida. `languages` é detectado na árvore quando o `bob.yaml` não existe ou a chave é omitida, e `[python]` fica só quando não há arquivo de fonte correspondente:

```yaml
base: origin/main
language: en
languages: [python]
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

Com `crap.scope: changed`, só funções alteradas bloqueiam. `all` faz toda função medida contar. O valor é `changed` ou `all`. `languages` omitido ou nulo é detectado pelos arquivos em `paths.include`, fora de `paths.exclude`. A varredura não segue symlink. `paths.exclude` casa por prefixo de caminho ou por componente, não por glob. `.py` escolhe `python`. `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs` e `.cjs` escolhem `typescript`, nessa ordem. Sem nenhum desses arquivos, o resultado é `[python]`. A mesma detecção roda quando o `bob.yaml` não existe e `--config` não foi passado. Uma lista explícita permanece como foi escrita. Uma lista vazia sai com `4`.

Se o YAML não é um mapeamento, se o YAML tem erro de sintaxe, se um mapeamento repete uma chave, ou se uma chave tem o tipo errado, a execução sai com `4`. A mensagem vai para o stderr em inglês e cita o arquivo. Um tipo errado também cita a chave, como em `bob.yaml: crap must be a mapping` ou `bob.yaml: crap.max_per_function must be a number`. Uma chave repetida cita a chave e a linha, como em `invalid YAML in bob.yaml: found duplicate key 'base' on line 2`. `check`, `doctor`, `waive` e os outros comandos fazem isso do mesmo jeito. Nenhum deles grava um arquivo.

Se `--config` aponta para um arquivo que não existe, `check`, `crap`, `dry`, `deps` e `mutate` saem com `4`. O stderr fica em inglês e cita o caminho que `load_config` recebeu (`config file not found: <caminho>`). Nada é gravado. `doctor` e `waive` não aceitam `--config`.

### Idioma da saída

O bob escreve o texto para humanos em inglês (`en`) ou em português do Brasil (`pt-BR`). Isso cobre as mensagens da CLI, o texto do `--help`, o `bob doctor`, o hook pre-push e o `.bob/report.md`. Vale a primeira fonte definida:

1. `--lang en|pt-BR`, antes ou depois do nome do comando.
2. A variável de ambiente `BOB_LANG`.
3. `language` no `bob.yaml`.
4. `en`.

A caixa importa (`pt-br` é inválido). Um `--lang` ou `BOB_LANG` vazio é inválido. A execução sai com `4`, imprime `invalid language: "" (use en or pt-BR)` no stderr e não grava nada. Uma chave `language` vazia no `bob.yaml` continua contando como ausente.

Um `--lang` ou `BOB_LANG` inválido, um `bob.yaml` que não é um mapeamento, um YAML com erro de sintaxe, ou uma chave com o tipo errado, sai com `4`. A mensagem vai para o stderr em inglês, mesmo quando `--lang` ou `language` é `pt-BR`. A execução não grava relatório nem `waivers.yaml`. `check`, `doctor`, `waive` e os outros comandos fazem isso do mesmo jeito. Um `duplication` inválido, uma chave desconhecida, um `language` numérico, um `language` que não é `en` nem `pt-BR`, um `crap.scope` que não é `changed` nem `all`, um item de `languages` que não é `python` nem `typescript`, um `crap.max_per_function` que não é um número finito maior que 0 (um inteiro grande demais para virar float também não é finito), uma lista `languages` vazia, um item de `languages` repetido, um `duplication.min_tokens` igual a 0 ou negativo, um `duplication.new_clones` que não é `warn` nem `fail`, um `duplication.max_new_clones` ou `duplication.min_lines` negativo, um `duplication.min_similarity` que não é um número finito de 0 a 100, um `waivers` igual a `0`, `false` ou `""`, e um `reason` vazio também saem com `4` em `check`, `doctor` e `waive`. O stderr em inglês cita o caminho e o campo, e a execução não grava nada.

O `.bob/report.json` tem os mesmos bytes nos dois idiomas. Todo `reason` de gate, o nome da regra de ciclo e o `reproduce` ficam em inglês, então uma ferramenta pode casar esse texto sem saber o idioma da saída. O `reproduce` do JSON não leva `--lang`. Em inglês a regra de ciclo se chama `Forbidden dependency cycle`. Em `pt-BR` ela se chama `Proibido ciclo de dependência` no `report.md` e no comentário do pull request. Uma regra do dependency-cruiser sem nome é `dependency` no JSON e `dependência` no Markdown. A linha de reprodução do `report.md` inclui o `--lang` que produziu o relatório.

No CI, defina `language: pt-BR` no `bob.yaml`, ou `BOB_LANG: pt-BR` no `env` do job. O input `language` da GitHub Action define a mesma escolha para o `bob check` e para o comentário do pull request. Um input vazio deixa `BOB_LANG` e o `bob.yaml` decidirem. A nota de truncamento do comentário e os erros do próprio comentário usam esse idioma.

### `bob doctor` e `--install`

`bob doctor` lista cada ferramenta com a versão pinada e a encontrada. Sai com `0` quando todas coincidem, e com `4` quando alguma falta ou diverge, junto com o comando de instalação. As ferramentas Python e npm precisam bater exatamente. O Node precisa estar em `>=22.18.0 <23`, então o Node 20, o Node 24 ou `22.18.0-rc.1` dá `4`. Se o diretório do pacote não for gravável, a mensagem pede `bob doctor --install`.

`bob doctor --install` roda `npm ci` no pacote instalado. Quando o npm falha ali com `EACCES`, `EPERM` ou `EROFS`, instala num cache do usuário (`$XDG_CACHE_HOME/bob-quality`, ou `~/.cache/bob-quality`). Outros erros do npm saem com `4` e o comando exato. Depois imprime o mesmo relatório.

### Waivers

Os waivers ficam em `.bob/waivers.yaml`, versionado junto com o código. `bob waive` grava uma entrada com estes campos:

- `id`, `arquivo::função` para todo sobrevivente da função, ou `arquivo::função::<descrição>` para um sobrevivente.
- `reason`, uma linha de texto.
- `author`, de `git config user.name`, ou `$USER`.
- `date`, a data em UTC.

Um waiver sem motivo de uma linha é rejeitado com exit `4`. `bob waive` de um id que já aparece uma vez substitui essa linha e sai com 0. Um arquivo que já contém duas linhas com o mesmo id sai com 4 e os bytes permanecem. A descrição é o operador do mutante, sem espaço nas pontas. No Python é o diff do `mutmut show`. No TypeScript é `{mutatorName}@{linha}:{coluna}-{linha}:{coluna}`, mais ` -> {replacement}` quando o Stryker traz o texto. A forma exata só existe quando nenhum outro sobrevivente da função tem a mesma descrição. A coluna Alvo da tabela de sobreviventes a mostra, ou mostra `—` quando ela não existe. `bob waive` só aceita o alvo de um sobrevivente da última mutação, lido de `.bob/mutation-cache.json` e `.bob/stryker-mutants.json`. Outro alvo, como o id do mutante ou o nome nu da função, sai com `4` e não grava nada. Um id editado à mão que não casa com nenhum sobrevivente deixa o sobrevivente sem waiver. No TypeScript, uma linha inserida acima do mutante muda a descrição, então o waiver antigo deixa de casar e o gate sai com `3`. Ver a [ADR 0006](docs/adr/0006-chave-estavel-do-waiver.md). Um `waivers.yaml` que é YAML válido com formato errado sai com `4`. A mensagem fica em inglês no stderr e cita `.bob/waivers.yaml` e o campo, como em `.bob/waivers.yaml: waivers[0].reason must be a string`. Uma lista no topo, um `waivers` que não é lista, um item que não é mapeamento e um campo ausente fazem isso. A execução não grava `report.md` nem `report.json`, e o arquivo permanece como está. `check`, `doctor` e `waive` fazem isso do mesmo jeito, mesmo quando `--lang` é `pt-BR`. Um erro de sintaxe YAML também sai com `4`. Essa mensagem cita `.bob/waivers.yaml` e o erro do parser. O agente grava o waiver, e o humano o aprova no review do pull request. Todo waiver aparece no topo do relatório.

### O relatório

`.bob/report.md` é uma página para quem revisa. `.bob/report.json` tem os mesmos dados e segue o schema em `src/bob_quality/schemas/report_v1.json` (`schema_version: 1`). `--format` escolhe um arquivo ou os dois. O relatório em Markdown tem estas partes, com os títulos no idioma da saída. Os nomes abaixo são os de `pt-BR`, e o `README.md` lista os de `en`:

1. `Waivers`, quando há waivers ou a mutação rodou.
2. Um cabeçalho com o commit, a base, a data e as versões das ferramentas.
3. `Veredito`, uma linha por gate: ✅ passou, ⚠️ aviso, ❌ falhou ou ⏭️ não executado com o motivo. Um gate que não rodou nunca aparece como ✅.
4. `Onde focar o review`, os arquivos alterados ordenados por risco (maior CRAP, mais clones e sobreviventes).
5. `Top 5 funções por CRAP (diff)`.
6. `Informação (dívida antiga)`, funções fora do diff no limite ou acima.
7. `Violações e ciclos de dependência`, e `Informação (dependências fora do diff)`.
8. `Clones novos`.
9. `Mutantes sobreviventes`.
10. `Rotatividade`, a contagem de commits e a taxa relativa (linhas alteradas divididas pelo tamanho do arquivo) dos arquivos alterados dentro dos caminhos incluídos. O título aparece sempre, e a seção não muda o código de saída.
11. `Como reproduzir`, o comando exato para rodar localmente, incluindo `--lang`. O mesmo comando no `report.json` não leva `--lang`.

A rotatividade conta os commits que o `git log` lista para cada arquivo alterado dentro de `paths.include`, em `churn.window_days` dias de calendário (padrão 90) terminando na data do próprio commit. O churn relativo de um arquivo é as linhas alteradas divididas pelo número de linhas dele. A taxa fica nula quando o arquivo não tem linhas ou não pode ser lido, e a contagem de commits permanece. O hotspot de uma função alterada é a contagem de commits vezes a complexidade ciclomática. A difusão é quantos desses arquivos mudaram e quantos diretórios pais eles ocupam. Quando a contagem não pode ser lida, o título fica e os números não. O campo no JSON é `churn`, e `schema_version` continua 1.

## Conceitos

### CRAP

O CRAP combina a complexidade de uma função com o quanto dela os testes executam. Uma função complexa e pouco testada é onde uma mudança tem mais chance de quebrar algo que ninguém vê, então o revisor olha ali primeiro.

```text
CRAP = CC² × (1 − cov)³ + CC
```

`CC` é a complexidade ciclomática medida pelo lizard. `cov` é a fração das linhas executáveis da função que os testes executaram, medida pelo coverage.py ou pelo c8. Uma função sem linhas executáveis conta como totalmente coberta.

| CC | Cobertura | CRAP | Resultado |
|---|---|---|---|
| 4 | 50% | 16 × 0.125 + 4 = 6 | passa |
| 5 | 0% | 25 × 1 + 5 = 30 | falha |
| 10 | 100% | 0 + 10 = 10 | falha |

O limite é CRAP < 10 por função alterada. Uma função com CRAP 10 ou mais reprova o gate com exit `1`. O gate roda os testes para medir a cobertura, então uma baseline quebrada dá exit `2`, também no `bob check` padrão. Como o CRAP nunca fica abaixo do CC, uma função alterada com CC 10 ou mais falha no limite padrão mesmo com cobertura total. Mude o limite com `crap.max_per_function` no `bob.yaml` ou com `bob crap --threshold`.

### Duplicação (DRY)

Um clone é um bloco de código que repete outro bloco. Clones novos mostram onde o agente copiou código em vez de reusar.

O bob roda o jscpd e fica só com os clones em que pelo menos um dos lados toca uma linha alterada. Depois, dois filtros escolhem quais clones novos entram na conta, nos dois modos. Um clone entra quando tem pelo menos `duplication.min_lines` linhas (padrão 0) e pelo menos `duplication.min_similarity` por cento de similaridade (padrão 0). Um clone sem percentual, como o exato, conta como 100. O jscpd já descarta clones com menos de 5 linhas, o padrão dele, então um `min_lines` abaixo de 5 não os traz de volta. Um clone fora da conta não aparece no relatório.

`duplication.new_clones` escolhe o modo. No modo `warn`, o padrão, o exit code continua `0`. Por exemplo, se o diff adiciona um bloco de pelo menos 50 tokens igual a um código que já existe, o relatório lista o par em `Clones novos` e o veredito mostra ⚠️. No modo `fail`, o gate mostra ❌ e sai com `1` quando a conta passa de `duplication.max_new_clones` (padrão 0), então um clone na conta já falha. O motivo cita a chave e o teto, como em `1 new clone exceeds duplication.max_new_clones 0`. Quando a conta fica no teto ou abaixo, o modo fail mostra ⚠️.

`bob dry` e `bob check` aceitam `--dry-fail`, que liga o modo fail nessa execução, e `--max-new-clones N`, que substitui o teto nessa execução. `0` é um teto de verdade. Nenhuma flag força o modo warn. Um `--max-new-clones` negativo sai com `4` antes de qualquer relatório. O hook pre-push não passa nenhuma das duas, então segue o `bob.yaml`.

`duplication.min_tokens` (padrão 50) é o mínimo de tokens do jscpd. Sem Node, o gate aparece como ⏭️ e o exit code continua `0`, também no modo fail.

### Teste de mutação

A cobertura mostra que uma linha rodou. Ela não mostra que um teste confere o resultado. O teste de mutação faz uma pequena mudança no código, chamada mutante, e roda os testes de novo. Se um teste falha, o mutante morreu. Se todos os testes continuam passando, o mutante sobreviveu, e aquela linha não está testada de verdade.

- `killed`, `survived`, `timeout` e `no_coverage` são os estados de um mutante. `no_coverage` quer dizer que nenhum teste executou o mutante.
- Um mutante equivalente muda o código sem mudar o comportamento, então nenhum teste consegue matá-lo. O bob não tem um estado separado para ele. Registre um waiver, como a skill `harden` descreve.
- Um waiver é um motivo de uma linha, aprovado pelo humano no review, para um sobrevivente que não deve ser morto.

Por exemplo, um mutante troca `if total > limit:` por `if total >= limit:`. Se nenhum teste usa `total == limit`, o mutante sobrevive. Escreva esse teste, ou rode `bob waive` com um motivo.

O bob muta Python com o mutmut e TypeScript com o Stryker. Ele roda os testes da baseline primeiro e sai com `2` se eles falham. Ele muta as funções alteradas, mais as funções que ainda têm sobreviventes sem waiver. O cache `.bob/mutation-cache.json` guarda um hash do texto de cada função. O reuso também exige que a versão do mutmut e a impressão da suíte batam. Uma diferença ainda remuta um sobrevivente sem waiver fora do diff. A GitHub Action restaura e publica o cache como o artefato `bob-mutation-cache`. O TypeScript guarda o arquivo incremental do Stryker em `.bob/stryker-incremental.json`. A Action restaura e publica esse arquivo no mesmo artefato. O mutmut roda em `.bob/mutmut/` e nunca escreve o `setup.cfg` nem o `mutants/` do repositório.

O limite é zero sobreviventes sem waiver numa linha alterada e zero mutantes `no_coverage` numa função alterada. Qualquer um reprova o gate com exit `3`. Sobrevivente sem waiver numa linha que o diff não mudou continua no relatório e não muda o exit. O relatório lista os sobreviventes e lista os `no_coverage` por função e arquivo. `killed` e `timeout` não bloqueiam. Um waiver não cobre `no_coverage`.

### Dependências

Regras de dependência e ciclos mostram erosão de arquitetura. Quando o módulo A importa B e B importa A, nenhum dos dois muda sozinho.

O bob roda as regras que o repositório já declara, em `.importlinter` para Python (import-linter) e em `.dependency-cruiser.cjs` para TypeScript (dependency-cruiser). Ele soma uma regra sempre ativa, que proíbe ciclos de dependência. O nome em inglês é `Forbidden dependency cycle`. O nome em `pt-BR` é `Proibido ciclo de dependência`. Por exemplo, se `app.a` importa `app.b` e o diff faz `app.b` importar `app.a`, o gate mostra ❌ e sai com `1`.

O limite é zero violações no diff. Uma violação só bloqueia quando a origem, o destino ou outro módulo do mesmo ciclo (componente fortemente conexo) foi alterado no diff. Violações antigas aparecem como `fora do diff; não bloqueia`.

## Hook pre-push

O script `src/bob_quality/hooks/pre-push` roda `bob check --gates crap,dry,deps`, os gates rápidos. Ele segue o `BOB_LANG` e o `language` do `bob.yaml`. `tests/test_hook.py` confere que ele termina em menos de 60 s no fixture.

```bash
cp src/bob_quality/hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

## Testes

```bash
pytest
```

Os repositórios-fixture estão em `tests/fixtures`: `python_app` (um caso que passa e um caso que falha por CRAP ≥ 10), `ts_app` e `mixed_app`. `tests/fixtures/raw` tem saídas gravadas das ferramentas pinadas.

O CI (`.github/workflows/ci.yml`) roda essa suíte em Python 3.10 e 3.12 com Node 22.18.0, em pull requests e em pushes para `main`.

## GitHub Action

A action composta em `.github/actions/bob` instala o `bob` e roda `bob check` com `crap,dry,deps,mutate`. Ela instala o Node 22.18.0 e o jscpd 5.4.1 antes, para o gate dry rodar quando quem chama a action não instalou os dois. Ela restaura e publica o artefato `bob-mutation-cache` (`.bob/mutation-cache.json` e `.bob/stryker-incremental.json`, guardado por 7 dias) e cria ou atualiza um único comentário no pull request com `.bob/report.md`. O exit code do job é o do `bob`, incluindo `4` para um uso inválido da linha de comando.

A action aceita os inputs `base`, `gates`, `pip-spec` e `token`. Este repositório a usa em `.github/workflows/bob.yml`. O `bob-quality` ainda não está no PyPI, então no checkout deste repositório a action roda `pip install -e ".[dev]"`, e em outro repositório instala o código-fonte git da action. Publicação no GitHub Marketplace não faz parte desta fatia.

## Publicação

[`.github/workflows/publish-plugins.yml`](.github/workflows/publish-plugins.yml) confere o plugin do Cursor numa tag `v*`, num release `published` e num `workflow_dispatch`. O job não envia o plugin. O formulário manual, a checagem de versão e a ausência de segredos estão em [docs/publishing.md](docs/publishing.md).

## Skills

- `skills/bob-check/` diz quando e como rodar `bob check`.
- `skills/harden/` diz como matar um mutante sobrevivente ou registrar um waiver.
- `skills/review-report/` resume `.bob/report.md` no pull request.
- `AGENTS.md` é o índice para agentes.
- `.claude-plugin/` e `.cursor-plugin/` são os manifestos do plugin. Veja [Instalação nos agentes](#instalação-nos-agentes).

## Créditos

Os gates seguem o fluxo do Uncle Bob. Os READMEs e as saídas das ferramentas dele [crapper](https://github.com/unclebob/crapper) e [mutator](https://github.com/unclebob/mutator) (0BSD) são a referência de comportamento, e o bob não reusa código delas. Os exit codes se inspiram no mutator. O gate de duplicação usa o jscpd. Um dryer estrutural próprio do bob, na linha do [dryer](https://github.com/unclebob/dryer) (0BSD) dele, fica fora do escopo do MVP. Os limites vêm dos posts recentes dele, CRAP < 10 para agentes ([post no X](https://x.com/unclebobmartin/status/2108946115169030596)) e matar mutantes dentro do razoável ([podcast da Aviator](https://www.aviator.co/podcast/uncle-bob-martin-ai-clean-code)).

As ferramentas de mercado (lizard, coverage.py, diff-cover, c8, vitest, mutmut, jscpd, import-linter, grimp, dependency-cruiser) são dependências pinadas, e o bob não copia código delas. grimp não tem adaptador.

## Licença

MIT. Ver `LICENSE`.
