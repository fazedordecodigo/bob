# CSS minificado, com e sem o override de postcss-selector-parser 7

Comparação do CSS emitido por `npm run build` em `website/`, Node 22.18.0, nos dois locales.

| | Sem o override | Com o override (`postcss-selector-parser` 7.1.6) |
|---|---|---|
| `postcss-minify-selectors` | `postcss-selector-parser` 6.1.4, aninhado | 7.1.6, hoisted (o override vale para a árvore inteira) |
| Pacote na raiz de `node_modules` | 7.1.6 (outros pacotes pedem `^7`) | 7.1.6 |
| Arquivo | `assets/css/styles.721eb682.css` | `assets/css/styles.721eb682.css` |
| Tamanho | 79732 bytes | 79732 bytes |
| sha256 (`en` e `pt-BR`, o mesmo arquivo) | `f546ec6f6531bc27afa8261e6cecd7ae9fb4e5a6d74a6363d723158e576aa2b2` | `f546ec6f6531bc27afa8261e6cecd7ae9fb4e5a6d74a6363d723158e576aa2b2` |

`diff -u` entre os dois arquivos: 0 linhas. O CSS minificado é idêntico. O override não muda o seletor publicado, inclusive `.markdown a` e os links da home.
