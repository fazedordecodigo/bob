# `bob update` e `bob --version`: implementação

Status: aceita pelo Emerson em 22/10/2026, no Plan Approval da U6, da U7 e da U8. Publicada em `docs/adr/` na U9.

## Decisão

- Rede (CT14): `urllib.request.urlopen(Request(url, headers=…), timeout=30)`. `Accept: application/vnd.github+json` só na chamada da API.
  - 3 tentativas, com 1 s de pausa (`time.sleep(1.0)`), como em `gitleaks.py`.
  - Repete só em erro de rede, timeout ou `5xx`. `4xx`, inclusive `429`, não repete.
  - Status no texto: `HTTP <código>`, senão o nome do tipo do `reason` (igual a `gitleaks._status`).
- `BOB_RELEASES_URL`: tira uma `/` final e valida com a mesma regex de `gitleaks._ALLOWED_URL`. Fora → `versão: BOB_RELEASES_URL=<v> …`, saída `4`.
- `tag_name` precisa casar `v\d+\.\d+\.\d+`. Senão → `versão: … (invalid response)`, saída `4`.
- Projeto: `setup_cmd.step_projeto(SetupContext(...))`. A mensagem é a do `bob setup`, com o prefixo `bob update:`. `BOB_HOME` relativo → `setup.bob_home_relative`, saída `4`.
- Comparação:
  - "pacote atual" = a tupla de `importlib.metadata.version("bob-quality")` ≥ a tupla da última. Versão local fora de `X.Y.Z` conta como mais velha.
  - "projeto atual" = estado `installed` com versão ≥ a última. `mixed` e `not_installed` nunca são atuais.
- Download: `install.sh`, depois `SHA256SUMS`, num `tempfile.mkdtemp(prefix="bob-update.")` que sai em `finally`.
  - `404` → "release incompleta"; outro erro → "download … falhou".
  - O `SHA256SUMS` é lido em bytes, por `line.partition(b"  ")`. Linha ausente ou hash diferente → `integridade`, `4`.
- Instalar: `subprocess.run(["sh", <script>, "--lang", <l>], cwd=<projeto>, env={**os.environ, "BOB_VERSION": <tag>}, check=False)`. Devolve o código do filho. `OSError` → `instalar: …`, `4`.
- `bob --version`: uma `argparse.Action` própria (`nargs=0`) no parser de topo. Imprime as 2 linhas e chama `parser.exit()`, que no `_Parser` vira `Help` e sai `0` antes da exigência de subcomando. O idioma vem de `_language` (`--lang`, `BOB_LANG`, `bob.yaml`).

## Consequências

São ~12 linhas parecidas com o `_fetch` do `gitleaks.py`. O gate `dry` só reporta, não bloqueia. Juntar as duas cópias fica para depois (fora da U7).
