# U2 — u2-doctor-fonte-unica — Desenho funcional (3.1 leve)

Unit: U2 | Kind: library | Dono de: C08 (`bob doctor`), C09 (fonte das versões npm) | Contrato: CT8 v1 | ADRs: 0008, 0019
Base lida: `fazedordecodigo/bob` `main` @ `d2e26bd1a75af1de48042af281ee418eb238fba8` (leitura remota pontual, sem clone). Data: 2026-10-18 20:51 UTC-3.

## Problema (P1)
- `doctor.py:70` espera vitest `5.0.4`. `package.json:15` pina `5.0.5` (commit #180 mudou só `package.json` e `package-lock.json`).
- Resultado na `main`: `bob doctor` sai `4`. O job `package/dist` falha (run 39159800688). O CI `pytest` também está vermelho: 18 falhas, 4065 passaram (run 39159800836). O commit anterior, `410175e`, estava verde.
- Causa: a versão npm existe em dois lugares (código e `package.json`). E o doctor olha `cwd/node_modules` (`doctor.py:358-360`, `437-441`), então o vitest do projeto pode mascarar o do bob.

## Regras de negócio
| # | Regra | Origem |
|---|---|---|
| R1 | As versões npm esperadas vêm só de `dependencies` do `package.json` empacotado (`src/bob_quality/package.json`; no checkout é symlink para a raiz; no wheel é arquivo real). Nenhuma versão npm literal em `doctor.py`. | ADR 0008, CT8, FR2.1 |
| R2 | A faixa do Node vem só de `engines.node` do mesmo arquivo. Forma aceita: `>=A.B.C <N` com `N = A + 1`. Hoje: `>=22.18.0 <23`. | ADR 0008, CT8 |
| R3 | Cada valor de `dependencies` é `X.Y.Z` exato (só dígitos). `^`, `~`, pré-release, número ou objeto: erro. | CT8 |
| R4 | Paridade: `package-lock.json` tem, para cada dependência, `packages["node_modules/<nome>"].version` igual ao `package.json`, e `packages[""].dependencies` igual a `dependencies`. Divergência → teste falha e cita pacote e as duas versões. | Pronto 3 |
| R5 | A versão npm encontrada vem só do prefixo do bob (`npm_prefix()`): `<prefixo>/node_modules/<pacote>/package.json`, campo `version`, com `name` igual ao pacote. Sem fallback para o executável no `PATH`. | ADR 0019 |
| R6 | O doctor não lê `Path.cwd()`, `cwd/node_modules` nem `cwd/node_modules/.bin`. Executáveis (`node`, `gitleaks`, ferramentas Python) vêm só do `PATH` (`shutil.which`). | I5, ADR 0019, FR2.5 |
| R7 | O doctor não escreve no projeto. Bytes alterados no cwd = 0. | NFR5, US1.4 crit. 1 |
| R8 | Sem `--install`, o doctor roda só 2 subprocessos: `node --version` e `gitleaks version`. | ADR 0019 (consequência de R5) |
| R9 | Saída do doctor preservada byte a byte: mesmas linhas `doctor.version`, mesma ordem de `PINS`, mesmos textos de instalação. Só muda o valor esperado (que agora vem do `package.json`). | CT8 |

## Fluxo `bob doctor` (sem `--install`)
1. Lê o `package.json` empacotado: `pinned_npm_versions()` e `node_range()`.
2. Para cada item de `PINS`, na ordem atual: Python (`importlib.metadata`), Node (`node --version`), npm (prefixo do bob), gitleaks (`gitleaks version`).
3. Imprime uma linha por item no stdout. Sai `0` se todos batem; `4` se algum diverge (com a linha de instalação ou `npm ci --prefix <prefixo>`, como hoje).

## Casos de erro e códigos de saída
| Caso | stdout | stderr (uma linha) | Exit |
|---|---|---|---|
| Tudo bate | linhas `doctor.version` | vazio | 0 |
| Ferramenta ausente ou versão diferente | linhas + instrução (igual a hoje) | vazio | 4 |
| `package.json` empacotado ausente/ilegível (`OSError`) | vazio | `bob doctor: package.json: não consegui ler <caminho> (<strerror>). Reinstale o bob.` | 4 |
| JSON inválido | vazio | `… (JSON inválido: <erro do json>). Reinstale o bob.` | 4 |
| Raiz não é objeto | vazio | `… (package.json não é um objeto). Reinstale o bob.` | 4 |
| `dependencies` ou `engines` ausente ou não objeto | vazio | `… (dependencies não é um objeto). …` / `(engines não é um objeto)` | 4 |
| Spec npm não exata | vazio | `… (dependencies.<nome> = <valor> não é X.Y.Z). …` | 4 |
| `engines.node` fora da forma | vazio | `… (engines.node = <valor> não é >=A.B.C <N com N = A + 1). …` | 4 |

- Em inglês (padrão): `bob doctor: package.json: could not read <path> (<detail>). Reinstall bob.`; detalhes `invalid JSON: …`, `… is not an object`, `… is not X.Y.Z`, `engines.node = … is not >=A.B.C <N with N = A + 1`.
- Formato CT1: `<prefixo>: <passo>: <o que falhou>. <ação>.` com prefixo `bob doctor` e passo `package.json`.
- Idioma: o mesmo `lang` que o doctor já recebe (`--lang`, `BOB_LANG`, `bob.yaml`, `en`).

## Interface (CT8, com refinamento)
- `bob_quality.npm_tools`: `class PinSourceError(ToolError)`; `pinned_npm_versions() -> dict[str, str]`; `@dataclass(frozen=True) class NodeRange(floor: tuple[int, int, int], below_major: int)`, `str()` = `">=22.18.0 <23"`; `node_range() -> NodeRange`.
- `bob_quality.doctor`: `node_range(pin: NodePin) -> str` fica. `node_admits` fica. `run_doctor(install, lang)` fica.
- **Refinamento de CT8 (técnico, sem consumidor fora dos testes):** a constante de módulo `NODE` sai. Entra `node_pin() -> NodePin`, lida sob demanda. Motivo: `cli.py` importa `doctor` no topo; ler o `package.json` no import quebraria todo comando do bob e impediria a regra "exit 4 com uma linha no stderr". Em `PINS`, a posição do Node é o marcador `NodeSlot()`. `NpmPin` fica `NpmPin(name, npm_package)`: perde `expected` (R1) e `executable` (R5, sem leitura no `PATH`).
- Consumidores: U1 (`node_range()` no passo `runtimes`; `run_doctor` no passo `doctor`), U8 (docs). Nenhum consumidor existe ainda no código além dos testes.

## Fora do desenho
- Docs que ainda dizem vitest `5.0.4` (README, `docs/*`): U8.
- Teste "install.sh tem a mesma faixa de Node/Python" de CT8: `install.sh` não existe. Vai para U1 (inconsistência I9, para o Maestro).
- Mocks com `5.0.4` em `tests/test_coverage_slots.py`: internos, passam, não leem o doctor.
