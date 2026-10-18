# Publicar o site de documentação

[Índice](README.md) · [ADR 0007](adr/0007-gerador-do-site.md)

O GitHub Actions publica o site Docusaurus no GitHub Pages em `https://fazedordecodigo.github.io/bob/`. O workflow é [`.github/workflows/pages.yml`](https://github.com/fazedordecodigo/bob/blob/main/.github/workflows/pages.yml).

A config do site permanece `url: 'https://fazedordecodigo.github.io'` e `baseUrl: '/bob/'`. Não há CNAME, nem domínio próprio, nem registro de DNS. O domínio `bob.fazedordecodigo.com` é uma mudança posterior ([#163](https://github.com/fazedordecodigo/bob/issues/163)).

## Configuração única

O Pages não está habilitado neste repositório. `GET /repos/fazedordecodigo/bob/pages` devolve 404. Este workflow não liga o Pages e não cria um secret. Habilitar o Pages com `actions/configure-pages` exigiria um token diferente de `GITHUB_TOKEN`, e o workflow define `enablement: false`.

O Emerson grava isso uma vez, nas configurações do repositório:

**Settings > Pages > Build and deployment > Source: GitHub Actions.**

Deixe o domínio próprio vazio. Não adicione um arquivo CNAME.

## Configurações do repositório

A origem do Pages é GitHub Actions, definida no passo acima. A regra recomendada de branch de deploy para o ambiente `github-pages` é só a `main`: **Settings > Environments > github-pages > Deployment branches and tags > Selected branches > `main`.** Uma execução do workflow a partir de qualquer outra ref não consegue publicar.

Enquanto a origem do Pages não estiver gravada, uma execução de deploy falha em `actions/configure-pages` ou `actions/deploy-pages`. As URLs ao vivo não devolvem HTTP 200, então ainda não há evidência de curl. O primeiro deploy verde, e a saída do `curl -I` abaixo, vêm depois dessa configuração e de o workflow estar na `main`.

## O que uma execução faz

O workflow roda em dois casos.

- Um push na `main` que altera `website/**` ou `docs/**`. Um commit que altera só o arquivo do workflow não publica. Dispare-o a partir da `main`.
- `workflow_dispatch` na `main`. O input `ref` é opcional e só escolhe a árvore a construir. Vazio constrói o commit da `main` em que o workflow roda.

O job de build tem `contents: read`. O checkout usa `persist-credentials: false` e faz checkout de `inputs.ref` quando ele está definido, senão de `github.sha`. Ele instala o Node `22.18.0` e em seguida roda `npm ci`, `npm run build` e `npm test` em `website/`. O artefato do Pages é `website/build`.

O job de deploy depende do job de build. O token dele tem `pages: write` e `id-token: write`, e nada mais. Ele roda no ambiente `github-pages`. Os passos são `actions/configure-pages` (`enablement: false`), `actions/deploy-pages` e depois a verificação de saúde. As três actions de Pages são as actions oficiais `actions/*`, pinadas por SHA de commit.

O grupo de concorrência é `pages`. Um deploy em andamento não é cancelado. Uma execução mais nova na fila substitui uma execução mais antiga na fila.

## Verificação de saúde

O job de deploy falha a menos que as duas URLs abaixo devolvam HTTP 200. Ele tenta de novo por uma janela curta de propagação: 10 tentativas, 10 segundos de intervalo, cerca de dois minutos.

```bash
curl --silent --show-error --head --output /dev/null --write-out '%{http_code}\n' --max-time 20 https://fazedordecodigo.github.io/bob/
curl --silent --show-error --head --output /dev/null --write-out '%{http_code}\n' --max-time 20 https://fazedordecodigo.github.io/bob/pt-BR/
```

As duas linhas têm de imprimir `200`. O job envia esse `HEAD` com `--write-out '%{http_code}'`, sem `-f` e sem seguir redirect. Os comandos acima acrescentam uma quebra de linha depois do código. Um `301` ou um `404` faz o job falhar. O job repete o pedido até 10 vezes, com 10 segundos de intervalo.

`actions/deploy-pages` publica o artefato antes da verificação. Uma verificação de saúde vermelha significa que o artefato novo já é público. Desfaça com um dos comandos abaixo. A verificação não despublica.

## Reversão

Nenhum secret é necessário. Só a `main` consegue publicar depois que o ambiente `github-pages` fica limitado a esse branch. Não dispare `pages.yml` a partir de outro branch ou tag.

### Revert na `main`

Este é o caminho que continua valendo depois da janela de 30 dias do GitHub para reexecutar.

```bash
git fetch origin main
git checkout main
git revert --no-edit <bad-commit-sha>
git push origin main
```

Alvo: `main`. O commit de revert tem de alterar `website/**` ou `docs/**`. Esse push é o que inicia o `pages.yml`. Se o commit ruim não tocou esses caminhos, dispare a partir da `main`.

Tempo esperado: cerca de 5 minutos do push até a verificação de saúde passar. O build é o mesmo trabalho do build do site no pull request, cerca de 3 minutos. A verificação de saúde então permite cerca de 2 minutos (10 tentativas, 10 segundos de intervalo). Se as duas URLs precisarem de todas as tentativas, a execução leva cerca de 7 minutos.

### Disparar o workflow na `main`

```bash
gh workflow run pages.yml --repo fazedordecodigo/bob --ref main -f ref=<commit-sha>
```

Alvo: o workflow roda na `main`. `<commit-sha>` é só a árvore a construir, e ela ainda precisa conter `website/` e `docs/`. Omita `-f ref=` para construir a ponta da `main`.

Tempo esperado: cerca de 5 minutos, ou cerca de 7 minutos quando a verificação de saúde usa todas as tentativas.

### Reexecutar uma execução bem-sucedida dos últimos 30 dias

O GitHub aceita `gh run rerun` por 30 dias depois da execução. Depois dessa janela, faça revert na `main`.

```bash
gh run list --repo fazedordecodigo/bob --workflow pages.yml --status success --limit 20
gh run rerun <run-id> --repo fazedordecodigo/bob
```

A execução reexecutada tem de ser uma que já rodou na `main`. A reexecução usa o commit e o snapshot do workflow dessa execução. A verificação de saúde roda de novo. Tempo esperado: cerca de 5 minutos, o mesmo de um dispatch na `main`.

## Depois do merge

Fazer merge desta mudança envia `docs/`, então o workflow começa na `main`. Essa execução fica vermelha até Source ser GitHub Actions. Depois que a configuração estiver gravada, reexecute o workflow que falhou (ele já rodou na `main`), ou dispare `pages.yml` a partir da `main`. Em seguida recolha a evidência:

```bash
curl -I https://fazedordecodigo.github.io/bob/
curl -I https://fazedordecodigo.github.io/bob/pt-BR/
```

Espere `HTTP/2 200` nas duas. Essa saída não está disponível a partir do pull request. O Pages ainda está desligado, e o site ainda não é servido.
