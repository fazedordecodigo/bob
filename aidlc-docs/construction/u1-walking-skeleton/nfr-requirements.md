# U1 — Requisitos não funcionais (3.2 leve)

Só os NFR que tocam a U1. Cada um com alvo numérico. Nenhuma meta existente do repo foi rebaixada.

| ID | Requisito | Métrica | Alvo | Origem |
|---|---|---|---|---|
| U1-N1 | Tempo de instalação (NFR1) | Wall clock do comando único num projeto novo, Linux x64, espelho local, rede do runner para PyPI e npm | ≤ 300 s | NFR1, pronto 2, passo 2 |
| U1-N2 | Um comando (NFR2) | Comandos que o dev digita para instalar, além de ter `python3`, `node`, `git`, `curl` | 1 | NFR2, US1.1 crit. 1 |
| U1-N3 | Sem privilégio (NFR7) | Chamadas ao `sudo` falso durante os passos 1, 2, 7, 8 e 9b | 0 (log com 0 bytes) | NFR7, pronto 5, passo 3 |
| U1-N4 | Idempotência (NFR4) | Na 2ª execução seguida: arquivos do projeto alterados; `npm ci` rodados; `versions/*` criados | 0; 0; 0 | NFR4, pronto 6, passo 7 |
| U1-N5 | Preservação (NFR5) | Bytes alterados em `.agents/skills/outra/**`, `package.json`, `node_modules/**` e `src/app.py` | 0 | NFR5, pronto 7, passo 8 |
| U1-N6 | Integridade do wheel (NFR6) | Com wheel adulterado (+1 byte): exit; `versions/` criados; arquivos do projeto alterados | `4`; 0; 0 | NFR6, pronto 8, passo 9b |
| U1-N7 | Clareza de erro (NFR9) | Falhas de `install.sh` e `bob setup` que saem em uma linha no stderr, formato CT1, com exit `4`, em en e pt-BR | 100% (todas as mensagens das ETs T3 e T4 têm teste por idioma) | NFR9, CT1 |
| U1-N8 | Falha cedo (US1.2) | Arquivos escritos (em qualquer lugar fora do `TMPDIR`) quando `projeto`, `plataforma`, `python`, `node` ou `ferramentas` falham | 0; `BOB_HOME` não existe | US1.2 crit. 1 e 3, pronto 4, passo 1 |
| U1-N9 | Skills num lugar só (ADR 0009) | Skills do bob em `.agents/skills`; em `.claude`, `.github`, `.cursor`, `.devin`; symlinks em `.agents/skills/**` | 3; 0; 0 | FR3.2, FR3.3, pronto 3, passo 4 |
| U1-N10 | Conteúdo do wheel (ADR 0010) | Entradas obrigatórias no `.whl`: 3 `SKILL.md`, `plugin.json`, `LICENSE` | 5 de 5 | pronto 9 |
| U1-N11 | POSIX (CT2) | `sh -n` e `dash -n` em `scripts/install.sh` e `scripts/verify-install.sh` | exit 0 nos dois | CT2, 3.6 |
| U1-N12 | Tempo do harness | `sh scripts/verify-install.sh` (passos 1, 2, 3, 4, 7, 8, 9b), Linux x64, cache do gitleaks frio | ≤ 900 s | novo (custo de CI) |
| U1-N13 | Leveza da 2ª execução | Tempo do comando único na 2ª execução (passo 7) | ≤ 60 s | novo; decorre de U1-N4 |
| U1-N14 | Qualidade do código (gates do repo) | `failed` + `errors` no CI `pytest` (3.10, 3.12); CRAP por função alterada; sobreviventes sem waiver; linhas novas de `src/` cobertas | 0; < 10; 0 (0 waivers novos); 100% (piso `coverage.min_percent` 80,0 mantido) | DoD 2, `bob.yaml`, `bob.yml` |
| U1-N15 | Segredos | Achados do gitleaks no PR | 0 | CI |
| U1-N16 | Paridade (I9, CT5, CT8) | Diferenças entre `install.sh` e Python em: faixa do Node, piso do Python, `BOB_HOME` (5 envs), opções de `curl`/`pip`, URLs padrão | 0 | ADR 0008, CT5, CT8, CT18 |
| U1-N17 | Rede | Hosts contatados pelo `install.sh` no modo espelho além de `127.0.0.1`, PyPI (índice do pip) e o registro do npm | 0 | CT14 |

## Não se aplica à U1 (ou só em parte)
- NFR3 (Linux e macOS, x64 e arm64): o código trata `Darwin`, `arm64` e `shasum`, mas a prova automática da U1 é só Linux x64. A matriz é da U9.
- NFR8 (hook rápido): U5.
- NFR6 do lado do gitleaks (tar.gz adulterado, passo 9a): U3.
- NFR10, NFR11 (prompt de IA): U8.
