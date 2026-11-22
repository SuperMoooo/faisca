# Faísca

Pesquisa de registos bibliográficos e de cópias digitais para catalogação em
UNIMARC.

- **Catálogos:** pesquisa ao mesmo tempo a PORBASE, o catálogo da BNP e
  outros catálogos nacionais e coletivos (Z39.50 e SRU). Converte os registos
  MARC21 para UNIMARC, junta os registos do mesmo livro e permite
  compará-los lado a lado.
- **Cópias digitais:** procura o livro na Biblioteca Nacional Digital,
  Europeana, Internet Archive, Open Library, Google Books e HathiTrust, e
  indica se o acesso é livre ou restrito.
- **Cesto de exportação:** junta registos de várias pesquisas num só
  ficheiro UNIMARC (ISO 2709, UTF-8) para importar no BIBLIO.NET.

Todas as pesquisas são feitas em direto nos serviços externos. O Faísca
guarda as respostas durante 24 horas, para não repetir pedidos, e **nunca
escreve no BIBLIO.NET**: a importação é sempre feita por quem cataloga.

O Faísca não tem contas nem palavra-passe: foi feito para correr no próprio
computador. Para o pôr num servidor, veja
[Implementar num servidor](#implementar-num-servidor-vps-com-https).

---

## Índice

1. [Estrutura do repositório](#estrutura-do-repositório)
2. [Correr no computador](#correr-no-computador)
3. [Configuração](#configuração)
4. [Implementar num servidor (VPS com HTTPS)](#implementar-num-servidor-vps-com-https)
5. [Catálogos e fontes configurados](#catálogos-e-fontes-configurados)
6. [Acrescentar um catálogo](#acrescentar-um-catálogo)
7. [Importar o ficheiro no BIBLIO.NET](#importar-o-ficheiro-no-biblionet)
8. [Conversão MARC21 → UNIMARC](#conversão-marc21--unimarc)
9. [A API e a futura app móvel](#a-api-e-a-futura-app-móvel)
10. [Desenvolvimento e testes](#desenvolvimento-e-testes)
11. [Limitações conhecidas](#limitações-conhecidas)

---

## Estrutura do repositório

```text
faisca/
├── backend/            API FastAPI (monólito modular, gerado com moarch-py)
│   ├── src/faisca/
│   │   ├── core/       configuração, logs, cliente HTTP, cortesia para com os serviços externos
│   │   ├── api/        /health e o router da /api/v1
│   │   └── modules/    um módulo por área; só falam entre si através de public.py
│   │       ├── records/          UNIMARC, conversão MARC21→UNIMARC, ISO 2709, duplicados
│   │       ├── catalogues/       pesquisa federada (Z39.50 via YAZ, SRU)
│   │       ├── digital/          cópias digitais (um adaptador por fonte)
│   │       ├── basket_items/     cesto de exportação
│   │       ├── cached_responses/ cache de 24 h (SQLite)
│   │       └── targets/          leitura de config/targets.yaml e verificação dos alvos
│   ├── migrations/     Alembic
│   ├── scripts/        export_openapi.py (gera contracts/openapi.json)
│   └── tests/          testes (sem rede: serviços externos simulados)
├── web/                interface web em Next.js (App Router, TypeScript), exportada como site estático
├── mobile/             reservado para a futura app Flutter (só um README)
├── contracts/          openapi.json: o contrato da /api/v1, partilhado pela web e pela app
├── config/targets.yaml catálogos e fontes de cópias digitais
├── Dockerfile          imagem única: backend + web exportada + config + YAZ
├── docker-compose.yml  para correr localmente
└── .env.example        variáveis de ambiente (chaves de API, cache, cortesia)
```

A interface web é um site estático (`next build` com `output: "export"`) que
o próprio FastAPI serve em `/`. Em produção há um só processo Python e um só
endereço: a web e a futura app móvel usam exatamente a mesma `/api/v1`.

---

## Correr no computador

### Com Docker (recomendado)

Precisa do [Docker Desktop](https://www.docker.com/products/docker-desktop/)
(Windows/macOS) ou do Docker Engine (Linux).

```bash
cp .env.example .env        # preencha CONTACT_EMAIL e, se tiver, EUROPEANA_API_KEY
docker compose up --build
```

Abra <http://localhost:8000>. A documentação interativa da API está em
<http://localhost:8000/docs>.

O contentor escuta só neste computador (127.0.0.1). A cache e o cesto ficam
num volume Docker (`faisca-data`) e sobrevivem a `docker compose down`.

### Sem Docker (para desenvolver)

Precisa de [uv](https://docs.astral.sh/uv/) e de Node.js 20.9 ou mais recente.

**Z39.50 precisa da biblioteca YAZ.** Em Debian/Ubuntu:
`sudo apt install libyaz5`; em macOS: `brew install yaz`. No Windows não há
pacote: os catálogos Z39.50 (PORBASE, BNP, Lisboa, Portimão, SBN) aparecem
como «Indisponível neste servidor» e os catálogos SRU funcionam na mesma.
Para ter tudo no Windows, use o Docker.

Num terminal, a API:

```bash
cd backend
uv sync
cp .env.example .env
uv run alembic upgrade head
uv run fastapi dev src/faisca/main.py        # http://127.0.0.1:8000
```

Noutro terminal, a interface web com recarregamento automático:

```bash
cd web
npm install
npm run dev                                   # http://localhost:3000
```

O `npm run dev` encaminha `/api` para a API em `127.0.0.1:8000` (outra porta:
`FAISCA_API_ORIGIN=http://127.0.0.1:8001 npm run dev`).

Para servir a web pela API, como em produção: `cd web && npm run build`; a
API passa a servir `web/out` em <http://127.0.0.1:8000>.

---

## Configuração

Tudo se configura com variáveis de ambiente, normalmente no ficheiro `.env`
(modelo em [.env.example](.env.example)). Nunca ponha chaves no código nem
no repositório: o `.env` está no `.gitignore` e no `.dockerignore`.

| Variável | Para quê |
| --- | --- |
| `CONTACT_EMAIL` | Vai no User-Agent de todos os pedidos externos, como os serviços pedem. Recomendado. |
| `EUROPEANA_API_KEY` | Chave gratuita em <https://pro.europeana.eu/page/get-api>. Sem ela, a Europeana não é pesquisada. |
| `GOOGLE_BOOKS_API_KEY` | Opcional. Sem ela, o Google Books usa uma quota anónima partilhada que costuma estar esgotada (HTTP 429). |
| `CACHE_TTL_HOURS` | Durante quanto tempo uma resposta é reutilizada (24 por omissão). |
| `MAX_RECORDS_PER_TARGET` | Registos lidos de cada catálogo por pesquisa (20). |
| `MAX_CONCURRENT_REQUESTS_PER_TARGET`, `MIN_SECONDS_BETWEEN_REQUESTS` | Cortesia: no máximo 2 pedidos em simultâneo e 1 segundo entre pedidos, a cada serviço. |
| `API_DOCS_ENABLED` | `/docs` com a documentação da API (ligado por omissão). |
| `ENVIRONMENT` | `production` escreve os logs em JSON, uma linha por evento. A imagem Docker já usa `production`. |

**Cortesia para com os catálogos.** Cada pesquisa vai a muitos serviços ao
mesmo tempo. Para que o Faísca nunca sobrecarregue nenhum deles:
- cada serviço tem limites próprios de pedidos em simultâneo e de intervalo
  entre pedidos;
- uma pesquisa repetida vem da cache;
- cada pedido identifica-se com um User-Agent e com o contacto indicado em
  `CONTACT_EMAIL`.

---

## Implementar num servidor (VPS com HTTPS)

O Faísca **não tem login**. Num servidor acessível da Internet, o acesso
tem de ser restringido à frente dele. Há duas formas simples:

- **Caddy com HTTPS e palavra-passe** (abaixo): qualquer navegador, com
  certificado Let's Encrypt automático.
- **Rede privada** ([Tailscale](https://tailscale.com/) ou WireGuard): o
  servidor fica invisível na Internet e só os seus dispositivos lá chegam.

Exemplo num VPS pequeno (1 vCPU, 1 GB de RAM chegam), com Debian ou Ubuntu,
Docker instalado e um domínio a apontar para o servidor:

```bash
git clone <este repositório> faisca && cd faisca
cp .env.example .env && nano .env                # CONTACT_EMAIL, chaves
docker compose up --build -d                      # escuta em 127.0.0.1:8000
```

Instale o [Caddy](https://caddyserver.com/docs/install) e crie
`/etc/caddy/Caddyfile`:

```caddy
faisca.exemplo.pt {
    # Gere o hash com: caddy hash-password
    basic_auth {
        catalogadora <hash da palavra-passe>
    }
    reverse_proxy 127.0.0.1:8000
}
```

```bash
sudo systemctl reload caddy
```

O Caddy obtém e renova sozinho o certificado HTTPS. O contentor tem
healthcheck (`/health`) e reinicia sozinho (`restart: unless-stopped`).

**Atualizar:** `git pull && docker compose up --build -d`. As migrações da
base de dados correm sozinhas no arranque.

**Instalar no telemóvel:** abra o endereço no Chrome (Android) ou no Safari
(iPhone) e escolha «Adicionar ao ecrã principal». O Faísca abre como uma
app; as pesquisas precisam de rede.

---

## Catálogos e fontes configurados

Verificados em direto a 2026-11-21 (pesquisa e leitura de registos). A
página **Definições** da aplicação mostra a lista e verifica, no momento, se
cada um responde.

**Catálogos**

| Catálogo | Protocolo | Formato | Notas |
| --- | --- | --- | --- |
| PORBASE | Z39.50 `z3950.porbase.bnportugal.gov.pt:210/porbase` | UNIMARC (ISO 5426) | Endereço publicado nos detalhes do serviço ZZZ |
| BNP, Catálogo | Z39.50 `z3950.catalogo.bnportugal.gov.pt:210/bn` | UNIMARC (ISO 5426) | Também alimenta a pesquisa da BND |
| Rede de Bibliotecas de Lisboa | Z39.50 `z3950.cm-lisboa.pt:210/rbml` | UNIMARC | Intermitente |
| BM Portimão | Z39.50 `z3950.bmmtgomes.pt:2100/biblios` | UNIMARC (UTF-8) | |
| Bibliothèque nationale de France | SRU | UNIMARC | |
| SUDOC (França) | SRU | UNIMARC | |
| SBN (Itália) | Z39.50 `opac.sbn.it:2100/nopac` | UNIMARC | Teve falhas temporárias |
| Biblioteca Nacional de España | SRU | MARC21 → UNIMARC | |
| K10plus (Alemanha) | SRU | MARC21 → UNIMARC | |
| swisscovery (Suíça) | SRU | MARC21 → UNIMARC | |
| Library of Congress | SRU | MARC21 → UNIMARC | |
| Deutsche Nationalbibliothek | SRU | MARC21 | **Desativado**: respondia 403 à rede de desenvolvimento |

**Ficaram de fora**, porque não aceitaram ligação ou não devolveram
registos nos testes:
- universidades: Porto, Aveiro, Coimbra e os três centros da Católica;
- Gulbenkian (Lisboa e Paris);
- bibliotecas municipais de Abrantes e Ponte de Lima;
- CCCM Macau e ISEG;
- bibliotecas nacionais da Austrália, Israel, Brasil e País de Gales;
- Yale, Finlândia, KB Dinamarca e Oxford (que exige credenciais).

A maioria só deve responder dentro da rede da própria instituição.

**Cópias digitais**

| Fonte | Como é pesquisada |
| --- | --- |
| Biblioteca Nacional Digital | Em direto no catálogo da BNP (Z39.50), ficando os registos com 856 $u para purl.pt. O OAI-PMH (set `bndlivre`) só serve recolha em lote, e o portal só devolve HTML. |
| Europeana | Search API (precisa de `EUROPEANA_API_KEY`) |
| Internet Archive | Advanced Search, só documentos de texto. Os livros só para empréstimo aparecem como acesso restrito. |
| Open Library | Search API, campo `ebook_access` |
| Google Books | `filter=free-ebooks` |
| HathiTrust | Bibliographic API, **só por ISBN** (a pesquisa de texto está atrás de Cloudflare) |
| Gallica | SRU. **Desativada**: o Cloudflare bloqueava a rede de desenvolvimento |

Para voltar a testar a DNB ou a Gallica a partir do servidor: em
`config/targets.yaml` mude `enabled: false` para `true`, reinicie e veja em
**Definições** se respondem.

---

## Acrescentar um catálogo

Edite [config/targets.yaml](config/targets.yaml), copie um bloco do mesmo
protocolo e reinicie a aplicação (`docker compose up --build -d`). A
aplicação recusa arrancar se o ficheiro tiver um erro, e diz qual.

**Onde encontrar os dados de ligação Z39.50:**
- Bibliotecas portuguesas: <https://zzz.porbase.org>. Em cada servidor da
  lista, o link «detalhes» mostra endereço, porta, base de dados e sintaxe.
- Registo internacional: [IRSpy, da Index Data](https://irspy.indexdata.com/).
- Ou a própria biblioteca (o fornecedor do sistema sabe).

**Z39.50:**

```yaml
  - id: bm-exemplo                # único, minúsculas, sem espaços
    name: Biblioteca Municipal de Exemplo
    country: PT                   # ISO 3166, duas letras
    protocol: z3950
    format: unimarc               # unimarc ou marc21: o que o servidor envia
    host: z3950.exemplo.pt
    port: 210
    database: biblios
    record_syntax: unimarc        # usmarc para MARC21
    charset: iso5426              # iso5426, marc8 ou utf-8 (ver abaixo)
    timeout_seconds: 15
    verified_on: 2026-11-21
    notes: Texto livre que aparece em Definições.
```

`charset` é o conjunto de caracteres do servidor. Se os acentos aparecerem
estranhos (`Lus´iadas`, `Baiäo`), experimente `iso5426`, e depois `utf-8`.
Os servidores portugueses mais antigos usam `iso5426`, o Koha usa `utf-8` e
a Library of Congress usa `marc8`.

Se o servidor pedir credenciais, acrescente `username:` e `password:`. A
palavra-passe nunca aparece na API nem na página **Definições**.

**SRU:**

```yaml
  - id: exemplo-sru
    name: Catálogo de Exemplo
    country: ES
    protocol: sru
    format: marc21
    url: https://exemplo.org/sru
    sru_version: "1.2"
    record_schema: marcxml        # ou unimarc / unimarcxchange, se o servidor tiver
    relation: "="                 # "all" em alguns servidores (BnF)
    indexes:                      # nomes CQL deste servidor (ver ?operation=explain)
      title: dc.title
      author: dc.creator
      isbn: bath.isbn
      year: dc.date               # opcional
      control_number: rec.id      # opcional: reabrir registos depois de a cache expirar
```

Os índices de cada servidor estão na resposta a
`<url>?operation=explain&version=1.2`.

**Uma nova fonte de cópias digitais** precisa de código: um adaptador em
`backend/src/faisca/modules/digital/sources/`, registado em
`sources/__init__.py`. Veja os adaptadores existentes.

---

## Importar o ficheiro no BIBLIO.NET

O BIBLIO.NET não é tocado pelo Faísca: descarrega o ficheiro e importa-o
pelos menus do próprio BIBLIO.NET. Os nomes exatos dos menus variam com a
versão e a configuração da sua instalação; os passos gerais são:

1. No Faísca, abra **Cesto** e carregue em **Descarregar … (ISO 2709)**. O
   ficheiro chama-se `faisca-unimarc-AAAAMMDD-HHMM.mrc`.
2. No BIBLIO.NET, abra o módulo de catalogação e procure a opção de
   importação de registos (normalmente «Importar» ou «Importação de
   registos», por vezes no menu de ferramentas ou de utilitários).
3. Escolha o ficheiro `.mrc`. Formato: **UNIMARC**. Estrutura: **ISO 2709**.
   Conjunto de caracteres: **UTF-8 / Unicode**.
4. Se o BIBLIO.NET mostrar uma pré-visualização, verifique os acentos num
   registo (por exemplo, «Lusíadas»). Se a importação controlar duplicados
   (por ISBN ou número de controlo), mantenha-a ligada.
5. Depois de importar, complete os dados locais: cotas, exemplares,
   localização, e os pontos de acesso de acordo com o seu ficheiro de
   autoridade.

**Recomendação:** na primeira vez, importe um só registo (o cesto pode ter
apenas um) e confirme o resultado antes de importar mais.

**Codificação.** O ficheiro está em UTF-8 e o diz: campo 100 $a, posições 26
a 29, `50`. Se a sua versão do BIBLIO.NET só aceitar ISO 5426 ou ISO 8859-1,
os acentos ficam trocados. Nesse caso:
- converta o ficheiro com o [MarcEdit](https://marcedit.reeset.net/)
  (MARC Tools, conversão de conjunto de caracteres), ou
- peça ao suporte do BIBLIO.NET a importação em UTF-8.

O YAZ não sabe *escrever* ISO 5426, por isso o Faísca não oferece essa
opção.

**Registos convertidos de MARC21.** Marcados com «MARC21, convertido».
Revalide sobretudo:
- os dados codificados (100, 101, 102, 105);
- as responsabilidades (700/701/702 e o código de função em `$4`);
- os assuntos, que mantêm o vocabulário de origem (LCSH, GND…) em `$2`.

---

## Conversão MARC21 → UNIMARC

Não existe um conversor MARC21 → UNIMARC mantido:
- o USEMARCON (última alteração em 2020) não traz regras para este sentido;
- os XSLT publicados e a especificação da Library of Congress vão no
  sentido contrário (UNIMARC → MARC21).

A conversão do Faísca segue essas tabelas ao contrário e o manual UNIMARC da
IFLA. O código está em
`backend/src/faisca/modules/records/marc21_to_unimarc.py` e as tabelas de
códigos em `marc21_unimarc_tables.py`.

**O que é convertido**

| MARC21 | UNIMARC |
| --- | --- |
| Líder | Líder (estado, tipo, nível bibliográfico e de codificação) |
| 001, 005 | 001, 005 |
| 020 / 022 / 024 / 010 / 035 | 010 / 011 / 016-017-073 / 020 / 035 |
| 008 | 100 $a (36 posições), 101, 102, 105 |
| 041 | 101 (com língua original em $c) |
| 245 | 200 ($a $e $d $f $g $h $i $b; artigo não ordenado com os marcadores NSB/NSE) |
| 250 | 205 |
| 260 / 264 | 210 |
| 300 | 215 |
| 490 / 440 / 8XX | 225 / 410 |
| 5XX | 300, 302, 320, 321, 323, 324, 325, 327, 328, 330, 333, 334, 336, 337, 371 |
| 76X-78X | 4XX (451, 452, 453, 454, 430, 440, 461) |
| 130 / 240, 246, 740 | 500, 510-517 |
| 600 / 610 / 611 / 630 / 650 / 651 / 655 / 653 | 600 / 601 / 605 / 606 / 607 / 608 / 610 |
| 080 / 082 / 050 / 084 | 675 (CDU) / 676 / 680 / 686 |
| 100 / 700 | 700 / 701 (coautores) ou 702 (outras funções), com códigos de função UNIMARC em $4 |
| 110 / 111 / 710 / 711 | 710 / 711 |
| 040 | 801 |
| 856 | 856 |

**Regras de limpeza:**
- A pontuação ISBD que o MARC21 guarda no fim dos subcampos
  (`Lisboa :`, `Os Lusiadas /`) é retirada, porque os sistemas UNIMARC a
  geram.
- Os artigos não ordenados (indicador 2 do 245, ou `<<Os>>` nos catálogos
  Alma e alemães) passam a U+0098/U+009C.
- Nos registos que já vêm em UNIMARC (PORBASE, BNP, BnF, SUDOC, SBN…), o
  registo é mantido tal como veio. Os acentos passam a UTF-8 (NFC) e o
  campo 100 passa a declarar Unicode.

O original MARC21 fica sempre disponível no ecrã do registo («MARC21
original», «Lado a lado») e pode ser descarregado.

**Registos repetidos.** Registos com um ISBN em comum são o mesmo livro.
Sem ISBN, um registo junta-se ao grupo com o mesmo título normalizado,
apelido do primeiro autor e ano. Dois ISBN diferentes nunca se juntam, mesmo
com o mesmo título, autor e ano (são encadernações ou tiragens diferentes).

---

## A API e a futura app móvel

A API está em `/api/v1`, com documentação interativa em `/docs` e o esquema
em `/openapi.json`.

| Pedido | O que faz |
| --- | --- |
| `GET /api/v1/catalogues/search?title=&author=&isbn=&year=&targets=` | Pesquisa federada; resultados parciais e o estado de cada catálogo |
| `GET /api/v1/records/{id}` | Um registo em UNIMARC e, se foi convertido, o MARC21 original (JSON) |
| `GET /api/v1/records/{id}/iso2709?variant=unimarc\|original` | O registo em ISO 2709 |
| `GET /api/v1/digital/search?title=&author=&isbn=&year=` | Cópias digitais e o estado de cada fonte |
| `GET / POST / DELETE /api/v1/basket`, `DELETE /api/v1/basket/{id}` | Cesto de exportação |
| `GET /api/v1/basket/export` | O cesto num ficheiro ISO 2709 |
| `GET /api/v1/targets`, `GET /api/v1/targets/status` | Alvos configurados e verificação em direto |
| `GET /health`, `GET /health/ready` | Estado do processo e da base de dados |

Os erros têm sempre a forma `{"error": {"code": "...", "message": "..."}}`.

**O contrato** está em [contracts/openapi.json](contracts/openapi.json),
gerado a partir do código (`uv run python scripts/export_openapi.py`, na
pasta `backend`):
- a web gera os seus tipos TypeScript a partir dele
  (`npm run generate:api`);
- a app Flutter vai gerar o seu cliente Dart a partir do mesmo ficheiro;
- o CI falha se o contrato e o código divergirem.

Na `/api/v1` só se acrescentam campos opcionais: mudanças incompatíveis vão
para uma `/api/v2`.

**Respostas de exemplo.** Com `MOCK_RESPONSES=true`, a API responde com
registos de exemplo, sem rede nem base de dados (cabeçalho
`X-Mock-Response: true`). Serve para desenvolver e testar a app sem
depender dos catálogos.

**A pasta `mobile/`** está reservada para a app Flutter (ver
[mobile/README.md](mobile/README.md)). Nunca entra na imagem Docker: está
excluída no `.dockerignore`, e o `Dockerfile` copia apenas `backend/`,
`web/` e `config/`.

---

## Desenvolvimento e testes

**Backend** (pasta `backend`; regras em [backend/AGENTS.md](backend/AGENTS.md)):

```bash
uv run ruff format . && uv run ruff check .
uv run mypy src tests
uv run lint-imports          # os módulos só usam o public.py uns dos outros
uv run pytest
```

Os testes não usam a rede:
- os catálogos são simulados com registos reais, guardados em
  `tests/fixtures/records` (Library of Congress, BNE, K10plus, BnF, SUDOC,
  PORBASE);
- as APIs de cópias digitais são simuladas com
  [respx](https://lundberg.github.io/respx/).

Cobrem:
- os auxiliares UNIMARC;
- a conversão MARC21 → UNIMARC com registos reais;
- a escrita ISO 2709, verificada com o leitor do pymarc;
- os registos repetidos;
- todos os endpoints.

**Web** (pasta `web`):

```bash
npm run typecheck
npm run lint
npm run build                # exporta para web/out
```

**Novo módulo no backend:** `moarch-py create module <nome>`. Gera todas as
camadas e o `public.py`.

O CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) corre tudo isto
e constrói a imagem Docker.

---

## Limitações conhecidas

- **DNB e Gallica** estão desativadas: bloqueavam a rede onde foram
  testadas. Volte a testá-las a partir do servidor.
- **Rede de Bibliotecas de Lisboa** responde de forma intermitente. O
  limite de 12 segundos evita que atrase toda a pesquisa.
- **SBN** teve falhas temporárias do lado do servidor. Os seus registos
  e os da BnF só reabrem enquanto estão em cache (24 h), porque esses
  servidores não aceitam pesquisa pelo número de registo. Os registos que
  já estão no cesto não são afetados.
- **Google Books** sem chave esgota a quota anónima com frequência.
- **HathiTrust** só é pesquisado quando há ISBN.
- **Registos repetidos sem ISBN:** livros com o mesmo título, autor e ano
  ficam no mesmo grupo, mesmo sendo edições de editoras diferentes. Abra o
  grupo («Escolher entre N registos») para ver as diferenças.
- **Número de resultados:** cada pesquisa lê os primeiros 20 registos de
  cada catálogo. Para obras com muitas edições, junte o autor, o ano ou o
  ISBN.
