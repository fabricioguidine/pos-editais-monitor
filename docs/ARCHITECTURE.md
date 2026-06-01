# Arquitetura — pos-editais-monitor

> Documento vivo. Última revisão: 2026-05-10.

## Princípios norteadores

1. **Clean Architecture / Hexagonal** — domínio puro, sem dependência de framework. Infra é
   *plugin* injetado.
2. **Async-first** — todo I/O (HTTP, DB, Redis, SMTP, LLM) é async. Não há `requests` síncrono
   no path de produção.
3. **Strategy + Registry para parsers** — cada fonte é uma estratégia, registrada em um único
   ponto. Adicionar uma fonte = uma classe + uma linha no registry, **zero** alteração em
   código orchestrator.
4. **Precision-first matching** — preferimos perder um edital marginal a notificar lixo.
5. **Auditabilidade** — todo edital tem snapshot original (HTML/PDF) + hash + spider + parser
   + timestamp. Reprodutibilidade total offline.
6. **Postura ética** — projeto monitora dados públicos, mas com restrição auto-imposta:
   `robots.txt`, rate limit baixo, sem proxies/stealth.

## Camadas

```
domain        ◀─ entidades, VOs, enums. Sem imports de fora.
  ▲
infrastructure ◀─ adapters: db, redis, llm, emec, smtp, storage. Implementa portas do domínio.
  ▲
scraping       ◀─ clients (httpx, playwright), middlewares, spiders (estratégias)
  ▲
parsers        ◀─ extrai campos estruturados de HTML/PDF/SIGAA
  ▲
pipeline       ◀─ orquestra fetch → parse → dedup → classify → persist → match → notify
  ▲
classification │
dedup          │ módulos especializados invocados pelo pipeline
matching       │
notifications  │
  ▲
scheduling     ◀─ jobs APScheduler (cron diário)
api            ◀─ FastAPI: read-only endpoints + admin protegido
cli            ◀─ typer: scrape | worker | dispatch-digest | refresh-emec
core           ◀─ config, logging, observability — usado por todas as camadas
```

### Camada `domain`

Apenas tipos puros — `Edital`, `Fonte`, `Snapshot`, `SubscriberProfile`, value objects de
período, identificadores, valores monetários (para bolsa). Enums de `Nivel`, `Modalidade`,
`StatusEdital`. Zero dependência de SQLAlchemy, FastAPI, Playwright etc.

Por quê: substituir Postgres por outra coisa ou rodar offline (replay sobre snapshot) não
deve afetar o domínio.

### Camada `infrastructure`

- `db/`: SQLAlchemy 2 async + Alembic. Modelos ORM mapeiam para entidades de domínio (1:1, com
  conversores `to_entity()` / `from_entity()`).
- `db/repositories/`: implementam Repository pattern. Pipeline depende da interface (Protocol),
  testes injetam in-memory.
- `cache/redis_client.py`: rate-limit token bucket, dedup TTL keys, response cache.
- `storage/object_store.py`: armazena HTML/PDF brutos. MVP usa filesystem local
  (`./storage/snapshots/<spider>/<date>/<hash>.html`); v0.3 troca por MinIO/S3 sem mudar API.
- `emec/client.py`: cliente para cadastro e-MEC com cache de 7 dias.
- `llm/anthropic_client.py`: wrapper sobre `anthropic.AsyncAnthropic` com prompt caching,
  retry, e métricas.

### Camada `scraping`

- `clients/http_client.py`: wrapper sobre `httpx.AsyncClient` com:
  - retry/backoff (`tenacity`) com jitter
  - rate limiter por host (token bucket em Redis — funciona entre workers)
  - circuit breaker por host (3 falhas em 60s → abre por 5min)
  - middlewares em cadeia (UA, robots, accept-language)
- `clients/playwright_client.py`: pool de browsers reutilizáveis. Lazy-init. Context per fetch
  para isolamento de cookies.
- `middlewares/robots_checker.py`: `protego` parser, cached por host.
- `spiders/base/spider.py`: classe abstrata `BaseSpider` com hooks:
  - `discover_urls() -> AsyncIterator[Url]`
  - `fetch(url) -> RawResponse`
  - `parse(raw) -> AsyncIterator[ParsedEdital]`
- `spiders/capes/`, `spiders/universities/ufrgs_spider.py`: implementações concretas.

### Camada `parsers`

Strategy pattern com registry. Cada parser implementa:

```python
class Parser(Protocol):
    name: str
    confidence_threshold: float
    def can_handle(self, raw: RawResponse) -> bool: ...
    async def parse(self, raw: RawResponse) -> ParsedEdital: ...
```

A função `resolve_parser(raw)` itera o registry e retorna o primeiro com `can_handle == True`.
Se a confiança do extrator for baixa, o pipeline pode invocar o parser LLM-fallback.

Sub-pacotes:
- `html/`: BeautifulSoup/selectolax para sites estáticos
- `pdf/`: `pdfplumber` (extrai layout) + `pypdf` (texto) + `pdf/llm_fallback.py`
- `sigaa/`: SIGAA tem estrutura muito padronizada — vale parser dedicado
- `wordpress/`: heurísticas para temas WP comuns em PPGs
- `fields/dates.py`: extração de datas em português brasileiro com `dateparser`/regex
- `fields/normalize.py`: normalização de texto (unicode, espaços, acentos)

### Camada `pipeline`

`PipelineOrchestrator` consome `ParsedEdital` produzidos pelos spiders e os passa por
**stages** em fila assíncrona (`asyncio.Queue` com backpressure):

```
fetch ─▶ parse ─▶ dedup ─▶ classify ─▶ persist ─▶ match ─▶ notify
```

Cada stage:
- consome de uma fila e produz para a próxima
- emite métrica Prometheus de items in/out/error
- erros vão para uma `dead_letter_queue` em Redis, retentável

Vantagem do design: scale workers por stage de forma independente. Se LLM fallback for o
gargalo, sobe-se mais workers só de `classify`.

### Módulos especializados

- `dedup/canonical_hash.py`: hash SHA-256 da forma canônica (texto normalizado + IES + nível
  + período). Detecta duplicatas exatas.
- `dedup/simhash.py`: simhash de 64 bits sobre tokens normalizados. Hamming distance ≤ 3 → mesmo
  edital com pequenas mudanças.
- `dedup/change_detector.py`: ao receber um item novo, busca o `Snapshot` anterior pelo
  `(fonte_id, identificador_externo)`. Se hash difere → cria novo snapshot e emite evento
  `EditalAtualizadoEvent`.
- `classification/rules_classifier.py`: dicionário CNPq + heurísticas (regex sobre nome do
  programa, área de concentração).
- `classification/llm_classifier.py`: chama Claude Haiku 4.5 (modelo barato/rápido) com prompt
  estruturado e cache de prompt.
- `classification/hybrid.py`: tenta rules; se confidence < 0.65 chama LLM.
- `matching/engine.py`: aplica perfil do subscriber. Hard filters + soft score.
- `notifications/dispatcher.py`: lê matches do dia, agrupa por subscriber, gera digest com
  Jinja2, envia por email (SMTP) e/ou telegram (aiogram).

### Camada `scheduling`

APScheduler com cron triggers:
- `00:00 *` (diário) — atualiza whitelist e-MEC
- `04:00 *` — corre todos spiders
- `07:00 *` — dispatch do digest do dia (último ciclo do scrape)
- `*/15 * * * *` — health check + métricas

### Camada `api`

FastAPI app expõe:
- `GET /v1/editais` — lista paginada com filtros (`nivel`, `modalidade`, `area`, `ies`)
- `GET /v1/editais/{id}` — detalhe + snapshots
- `GET /v1/fontes` — fontes ativas
- `GET /v1/subscribers/me` — perfil
- `POST /v1/subscribers/me` — atualiza perfil (auth via API key)
- `GET /healthz`, `GET /readyz`, `GET /metrics`

### Camada `cli`

Typer-based:
- `pem scrape --source <name>` — roda 1 spider
- `pem worker` — sobe scheduler + pipeline (modo daemon)
- `pem dispatch-digest [--dry-run]` — envia digest agora
- `pem refresh-emec` — força refresh do cache
- `pem replay --snapshot-id <id>` — re-processa um snapshot (debug)

## Fluxo de dados ponta a ponta (exemplo concreto)

1. **04:00** — APScheduler dispara `job_run_all_spiders`.
2. `CapesSpider.discover_urls()` itera as listagens do portal CAPES e produz ~80 URLs candidatas.
3. Para cada URL, `HttpClient.get(url)`:
   - checa robots.txt → permitido
   - aguarda token do rate limiter (~2s entre requests pro mesmo host)
   - faz GET com retry+backoff
   - armazena resposta crua em `storage/snapshots/capes/2026-05-10/<sha>.html`
4. `parser_registry.resolve(raw)` retorna `CapesHtmlParser`.
5. Parser extrai `ParsedEdital(titulo=..., nivel=..., ies="UFMG", area=..., prazo=..., is_gratuito=True, link_pdf=...)`. Se houver `link_pdf`, faz fetch do PDF e roda `PdfParser`.
   - Se confidence < 0.65 → invoca `PdfLlmFallback` (Claude Haiku).
6. **Dedup**: calcula `canonical_hash`. Busca em DB. Não existe → novo `Edital` e `Snapshot`.
7. **Classify**: rules dizem `area_cnpq=10300007 (Ciência da Computação)` com confidence 0.92.
8. **Persist**: insere `Edital`, `Snapshot`, vínculo `Fonte`. Emite evento `EditalNovoEvent`.
9. **Match**: para cada `SubscriberProfile`:
   - hard filters: gratuito ✓, IES na whitelist e-MEC ✓, nível mestrado ✓.
   - soft score: área `10300007` = match exato com peso 1.0 → score=1.0.
   - 1.0 ≥ 0.70 → cria `MatchRecord(subscriber=fabricio, edital_id=..., score=1.0)`.
10. **07:00** — `dispatch_digest_job` consulta `MatchRecord` do dia para cada subscriber. Se
    existir ≥ 1, renderiza template Jinja2 e envia via `aiosmtplib`.

Cada passo emite log estruturado e métrica.

## Testes e portabilidade

A pirâmide de testes é organizada por marker para isolar I/O externo:

- **`tests/unit`** — funções puras (parsing de campos, datas, normalização, dedup,
  classificação, whitelist e o `MatchEngine`). Sem rede, SMTP, Docker ou DB.
- **`tests/e2e`** — suite **end-to-end hermética**. Alimenta documentos sintéticos
  (HTML em `tests/fixtures/html/` e um PDF mínimo válido em `tests/fixtures/pdf/`)
  nos **parsers reais** (`WordPressParser`, `GenericHtmlParser`, `PdfParser`),
  aplica o mesmo mapeamento `ParsedEdital → Edital` do orchestrator, roda
  classificação + matching contra um perfil sintético (assertando que **apenas
  verdadeiros positivos** passam) e verifica a **composição do digest** via um
  canal fake que captura o `NotificationPayload` — **nenhum envio real**. Tudo
  determinístico e OS-agnóstico (`tmp_path`, fixtures relativas ao pacote).
- **`tests/integration`** (marker `integration`) — exige Postgres + Redis.
- **`tests/contracts`** (marker `contract`) — bate em upstreams reais; nightly.

**Cross-platform.** O domínio e os parsers não dependem de SO: caminhos via
`pathlib`, `encoding="utf-8"` em toda leitura de arquivo, configuração só por
variáveis de ambiente (`PEM_*`), nenhum diretório absoluto embutido, e o object
store normaliza o path lógico para `/`. A CI valida o caminho rápido
(`tests/unit` + `tests/e2e`) numa matriz **{ubuntu, macos, windows} × {3.11, 3.12, 3.13}**.

## Decisões registradas (ADRs)

- [ADR-0001 — Clean architecture com domínio puro](adr/0001-clean-architecture.md)
- [ADR-0002 — Pipeline async com asyncio.Queue](adr/0002-async-pipeline.md)
- [ADR-0003 — Parsing híbrido com LLM fallback](adr/0003-hybrid-parsing-llm-fallback.md)
- [ADR-0004 — Dedup simhash + canonical hash](adr/0004-simhash-deduplication.md)
- [ADR-0005 — Scraping respeitoso e auditável](adr/0005-respectful-scraping.md)
- [ADR-0006 — e-MEC como whitelist obrigatória](adr/0006-emec-whitelist.md)
- [ADR-0007 — Matching precision-first](adr/0007-matching-precision-first.md)
- [ADR-0008 — Email como canal primário](adr/0008-email-primary-channel.md)

## Trade-offs explícitos

| Decisão                                | Ganho                                 | Custo                                          |
|----------------------------------------|---------------------------------------|------------------------------------------------|
| Clean Architecture pura no domínio     | Testabilidade, swap de infra          | Mapeamento ORM↔domínio (boilerplate)           |
| Async em tudo                          | Concorrência alta com poucos threads  | Curva mais íngreme, libs sync ficam de fora    |
| Playwright pool                        | Suporta SIGAA e sites JS-heavy        | Memória alta (~150MB por contexto)             |
| LLM fallback                           | Resiliente a HTML caótico             | Custo por call + latência (~1-3s)              |
| Simhash dedup                          | Detecta variações pequenas            | Tuning de threshold é empírico                 |
| Precision-first matching               | Email útil de verdade                 | Pode perder edital marginal                    |
| Rate limit 0.5 RPS                     | Postura ética, sem bloqueios          | Coleta diária é lenta (~80 req = ~3 min)       |
| Single-binary CLI (typer)              | Onboarding simples                    | Pode crescer monolítico — extrair se necessário |

## Riscos conhecidos

1. **Mudança de HTML upstream** — mitigado por contract tests nightly + alertas.
2. **PDF mal formatado** — mitigado por LLM fallback + snapshot para replay.
3. **e-MEC indisponível** — mitigado por cache 7 dias + degradação graciosa (usa snapshot prévio).
4. **Custo LLM crescente** — mitigado por prompt caching (5min TTL Anthropic) + threshold ajustável.
5. **Falso positivo no matching** — mitigado por threshold alto + feedback loop manual via CLI.

## Melhorias futuras

- **Webhook outbound** para integrar com Slack/Discord (v0.4).
- **API pública** com OpenAPI + cliente TypeScript gerado (v0.4).
- **Replay determinístico** com Time-Travel sobre snapshots — debugar regressão em parser (v1.0).
- **Auto-aprendizagem de seletores quebrados** com diff de DOM + LLM (v0.3).
- **Multi-subscriber com OAuth** para virar SaaS lite (v1.0).
- **Mutation testing** na camada de matching para garantir robustez (v1.0).
