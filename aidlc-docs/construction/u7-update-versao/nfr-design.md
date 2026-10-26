# U7 — Desenho dos NFR (3.3 leve)

| Id | Como o desenho atende | Onde se prova |
|---|---|---|
| U7-N1, N4 | O `bob update` não grava nada no projeto: delega ao `install.sh` da tag (com `BOB_VERSION`), que reusa o `bob setup` e as regras de posse da U1–U5. | passo 10 |
| U7-N2 | Só `releases/latest` é lida. O espelho serve a pré-release e o rascunho em caminhos que o `latest` não aponta. A lista exata de pedidos prova que nenhum foi tocado. | passo 10 |
| U7-N3 | A comparação vem antes de qualquer download. "Atual" exige pacote ≥ última **e** projeto `installed` ≥ última (I3). | passo 11; testes 1–2 da T2 |
| U7-N5 | Hash conferido antes de gravar o script no disco e antes do `sh`. Linha lida em bytes, sem decodificar. | testes de integridade da T2 |
| U7-N6 | Mesmas constantes de rede do `gitleaks.py`, presas por teste (`test_constants_match_install_sh_and_gitleaks`). `urlopen` falso nos testes conta tentativas, cabeçalhos e `timeout`. | T2 |
| U7-N7, N8 | O wheel novo é o do build rebatizado, então não há segundo build. O `pacote` cria só 1 venv novo. O passo 11 não baixa nada. | job |
| U7-N13 | `urlopen` e `subprocess.run` trocados nos testes. O único processo real é `sh` com um `install.sh` falso, sem rede. Git só em `tmp_path`. | `tests/test_hermetic.py` |
