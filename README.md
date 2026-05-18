# pos-editais-monitor

> Monitoramento automatizado, respeitoso e auditável de editais de pós-graduação **gratuitos** no Brasil.

[![CI](https://github.com/fabricioguidine/pos-editais-monitor/actions/workflows/ci.yml/badge.svg)](https://github.com/fabricioguidine/pos-editais-monitor/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

---

## Sumário

- [O que é](#o-que-é)
- [Por que existe](#por-que-existe)
- [Como funciona (fluxo de alto nível)](#como-funciona-fluxo-de-alto-nível)
- [Stack](#stack)
- [Arquitetura](#arquitetura)
- [Fontes monitoradas](#fontes-monitoradas)
- [Matching personalizado](#matching-personalizado)
- [Postura ética de scraping](#postura-ética-de-scraping)
- [Rodando localmente](#rodando-localmente)
- [Roadmap](#roadmap)
- [Observabilidade](#observabilidade)
- [Diferenciais técnicos](#diferenciais-técnicos-para-portfólio-sdetqa)
- [Documentação adicional](#documentação-adicional)

---

## O que é

Sistema que **descobre, normaliza, deduplica, classifica, filtra e notifica** sobre editais de
pós-graduação gratuitos (especialização, MBA, mestrado, doutorado, UAB/EAD) publicados por:

- **CAPES** — programas, chamadas e bolsas
- **UAB** (Universidade Aberta do Brasil)
- **Universidades federais e institutos federais** (whitelist via cadastro **e-MEC**)
- **Portais SIGAA** (sistema acadêmico usado por dezenas de IFES)
- **Diário Oficial da União** (quando publica chamadas de pós)
- Páginas WordPress de PPGs (padrão extremamente comum entre PPGs federais)

A saída é um **digest diário por email**, enviado **apenas quando há matches** contra o
perfil acadêmico do assinante. Sem notificação de ruído.

## Por que existe

A informação existe — mas está fragmentada em **centenas de portais com layouts diferentes**,
muitas vezes apenas em PDF, frequentemente sem feed RSS, muitas vezes mudando de URL a cada
edição. Acompanhar manualmente é inviável.

Este projeto resolve isso como um **pipeline ETL especializado em editais**, com foco em três
propriedades de engenharia:

1. **Resiliência** — sobreviver a mudanças de HTML, falhas de rede e PDFs malformados.
2. **Precisão de matching** — `precision >> recall`. Email só com algo realmente relevante.
3. **Auditabilidade** — para cada edital notificado, é possível rastrear de qual URL, em qual
   timestamp, com qual hash, com qual parser, e por qual razão foi classificado como match.

## Como funciona (fluxo de alto nível)

```
┌──────────────┐    ┌─────────────────┐    ┌──────────────┐    ┌──────────────┐
│   Scheduler  │───▶│  Spider (HTTP/  │───▶│   Parser     │───▶│   Dedup +    │
│  (APSched.)  │    │   Playwright)   │    │ (HTML/PDF/   │    │ ChangeDetect │
└──────────────┘    │  + RateLimiter  │    │  SIGAA/LLM)  │    └──────┬───────┘
                    │  + RobotsCheck  │    └──────┬───────┘           │
                    │  + e-MEC gate   │           │                   ▼
                    └─────────────────┘           ▼            ┌──────────────┐
                                          ┌──────────────┐    │  Classifier  │
                                          │  Persist     │◀───│  (rules +    │
                                          │  (Postgres + │    │   LLM fb)    │
                                          │   snapshot)  │    └──────┬───────┘
                                          └──────────────┘           │
                                                                     ▼
                                                              ┌──────────────┐
                                                              │   Matcher    │
                                                              │  (profile-   │
                                                              │   based)     │
                                                              └──────┬───────┘
                                                                     │  matches?
                                                              ┌──────▼───────┐
                                                              │ Email digest │
                                                              │  (Jinja2 +   │
                                                              │   SMTP)      │
                                                              └──────────────┘
```

## Stack

| Camada              | Tecnologia                                                     |
|---------------------|----------------------------------------------------------------|
| Linguagem           | Python 3.11+                                                   |
| API                 | FastAPI + Uvicorn                                              |
| HTTP client         | httpx (async, HTTP/2) + tenacity (retry/backoff)               |
| Browser automation  | Playwright (async, headless Chromium) — usado *só* quando necessário |
| HTML parsing        | BeautifulSoup, lxml, selectolax                                |
| PDF parsing         | pdfplumber + pypdf + fallback LLM (Claude)                     |
| Persistência        | PostgreSQL 16 + SQLAlchemy 2 async + Alembic                   |
| Cache / queue       | Redis 7                                                        |
| Scheduler           | APScheduler (cron-based)                                       |
| Notificações        | aiosmtplib (email primário) + aiogram (telegram opcional)      |
| Observabilidade     | structlog + OpenTelemetry + Prometheus                         |
| Testes              | pytest, pytest-asyncio, respx, hypothesis, factory_boy         |
| Lint/format/type    | ruff + mypy strict                                             |
| Containerização     | Docker multi-stage + docker compose                            |
| CI                  | GitHub Actions                                                 |

## Arquitetura

Aplicação organizada em **camadas** seguindo princípios de **Clean Architecture / Hexagonal**:

```
src/pos_editais_monitor/
├── domain/              # entidades puras, value objects, enums (zero dependências externas)
├── infrastructure/      # adaptadores: db, redis, storage, llm, emec, smtp
├── scraping/            # spiders, http/playwright clients, middlewares (rate, robots, CB)
├── parsers/             # strategy pattern: html, pdf, sigaa, wordpress + registry
├── pipeline/            # orchestrator async, stages (fetch→parse→dedup→classify→persist→match→notify)
├── dedup/               # canonical hash, simhash, change detector entre snapshots
├── classification/      # CNPq areas + rules + LLM hybrid
├── matching/            # subscriber profile + score engine (precision-first)
├── notifications/       # dispatcher + email/telegram channels + Jinja2 templates
├── scheduling/          # APScheduler jobs (cron diário)
├── api/                 # FastAPI app + routers + schemas + dependencies
├── core/                # config (pydantic-settings), logging (structlog), obs (OTEL/metrics)
└── cli/                 # typer-based CLI: pem scrape | worker | dispatch-digest
```

Veja [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) para o detalhamento de cada camada, fluxos
de dados, e as decisões registradas em [`docs/adr/`](docs/adr/).

## Fontes monitoradas

A **whitelist de IES** vem do cadastro oficial **[e-MEC](https://emec.mec.gov.br)** —
o pipeline **não processa** edital de instituição que não esteja:

- ativa e credenciada (`situacao_cadastral = ATIVA`)
- categorizada como pública/gratuita (federais, estaduais, IFs, CEFETs, UAB)

A whitelist é cacheada por 7 dias (mudanças cadastrais são raras), com refresh forçado por
CLI (`pem refresh-emec`).

A estratégia detalhada está em [`docs/SOURCES.md`](docs/SOURCES.md). MVP foca em Tier 1:

| Fonte                              | Papel               | Mecanismo          | Status MVP |
|------------------------------------|---------------------|--------------------|------------|
| **DOU (Imprensa Nacional)**        | editais oficiais    | API JSON           | ✅         |
| **Sucupira CAPES**                 | catálogo de PPGs    | httpx + BS4        | ✅         |
| **e-MEC**                          | whitelist IES       | httpx + cache 7d   | ✅         |
| SIGAA federado (40+ IES)           | editais de IFES     | Playwright         | 🟡 v0.2    |
| WordPress PPGs (RSS-first)         | editais de PPGs WP  | httpx + RSS/BS4    | 🟡 v0.2    |
| UAB                                | EAD pública         | httpx + BS4        | 🟡 v0.2    |
| Per-IES (USP, Unicamp, UFRGS, ...) | Tier 3 dedicado     | httpx + BS4        | 🟡 v0.3    |

## Matching personalizado

Cada subscriber tem um **perfil** que descreve o que ele aceita receber:

```yaml
profile:
  nome: fabricio
  formacao: bacharelado_ciencia_computacao
  areas_alvo:
    - codigo_cnpq: "10300007"        # Ciência da Computação
      modo: exact
      peso: 1.0
    - codigo_cnpq: "40000004"        # Ciências da Terra (Geociências)
      modo: cross_discipline
      requer_aceita_cs: true         # só conta se edital aceitar CS
      peso: 0.7
  niveis_aceitos: [especializacao, mba, mestrado, doutorado]
  modalidades_aceitas: [presencial, ead, semipresencial]
  apenas_gratuitos: true
  apenas_ies_emec_publicas: true
  score_minimo: 0.70
```

O `MatchEngine` aplica **hard filters** (eliminatórios) seguidos de **soft scoring**:

1. **Hard filters** (qualquer um falso → descartado):
   - `edital.is_gratuito == True`
   - `edital.ies in emec_whitelist_publicas`
   - `edital.nivel in profile.niveis_aceitos`
   - `edital.modalidade in profile.modalidades_aceitas`

2. **Soft score** (combina contribuições e compara com `score_minimo`):
   - Match exato de área CNPq → soma `peso`
   - Match `cross_discipline` válido → soma `peso` se `requer_aceita_cs` satisfeito
   - Sem match → 0

Apenas quando `score >= 0.70` o edital entra no digest. Filosofia: **precision over recall** —
preferimos perder um edital marginal a entregar 30 emails irrelevantes por semana.

## Postura ética de scraping

Este projeto monitora **sites públicos** de instituições públicas. Mesmo assim adota uma
postura conservadora e auditável:

- **`robots.txt` é respeitado** por padrão. Cada spider verifica antes de fetch.
- **User-Agent identificável** com URL do projeto e email de contato.
- **Rate limit conservador**: 1 req a cada 2s por host (configurável via `PEM_RATE_LIMIT_RPS`).
- **Sem rotação de proxies, sem stealth fingerprinting, sem CAPTCHA solver.**
- **Playwright apenas para sites JS-heavy** (SIGAA é o principal caso). Páginas estáticas
  vão por httpx, que é ~30x mais barato.
- **Cache de respostas** em Redis com TTL para evitar re-fetch desnecessário.
- **Backoff exponencial** + circuit breaker — se um site retornar 5xx, recuamos.

Detalhes em [`docs/SCRAPING_STRATEGY.md`](docs/SCRAPING_STRATEGY.md) e
[ADR-0005](docs/adr/0005-respectful-scraping.md).

## Rodando localmente

### Pré-requisitos

- Python 3.11+
- Docker + Docker Compose
- (opcional) [uv](https://github.com/astral-sh/uv) para gerenciar venv mais rápido

### Setup

```bash
git clone https://github.com/fabricioguidine/pos-editais-monitor
cd pos-editais-monitor
cp .env.example .env
# edite .env com seu ANTHROPIC_API_KEY, SMTP password (App Password do Gmail), etc.

make dev              # cria venv, instala deps, instala playwright, pre-commit
make compose-up       # sobe Postgres + Redis
make migrate          # aplica migrations
make run-api          # API em http://localhost:8000  (swagger em /docs)
```

Em outro terminal:

```bash
make run-worker       # inicia scheduler + pipeline async (corre em loop)
```

Para rodar um spider ad-hoc:

```bash
uv run pem scrape --source capes
uv run pem scrape --source ufrgs-ppg
uv run pem refresh-emec
uv run pem dispatch-digest   # envia o digest do dia agora (não espera o cron)
```

### Testes

```bash
make test-unit              # rápido, sem rede, sem DB
make test-integration       # exige PG e Redis up (docker compose)
make test-contracts         # bate em sites reais (CI roda nightly, não em PR)
```

## Roadmap

Visão por milestones — detalhes em [`docs/ROADMAP.md`](docs/ROADMAP.md).

- **v0.1 (MVP) — em construção**
  - CAPES + UFRGS PPG ponta a ponta
  - e-MEC whitelist
  - Dedup simhash + change detector
  - Classifier rules + LLM fallback (Claude)
  - Matcher precision-first
  - Email digest diário
  - Docker compose, CI green, coverage ≥ 75%

- **v0.2** — UAB + SIGAA (Playwright) + alertas Telegram + dashboard básico

- **v0.3** — DOU + IFs + ICs auto-aprendizagem de seletores quebrados

- **v0.4** — multi-subscriber + API pública + Webhook outbound

- **v1.0** — observabilidade completa (Grafana dashboards) + replay determinístico de snapshots

## Observabilidade

- **Logs** estruturados (JSON em prod, console color em dev) via `structlog`. Cada log tem
  `request_id`, `spider`, `source`, `url_hash`, `stage`, `latency_ms`.
- **Traces** OpenTelemetry instrumentando FastAPI, httpx e SQLAlchemy. Exporter OTLP opcional.
- **Métricas** Prometheus (port 9090):
  - `pem_spider_requests_total{spider,status}`
  - `pem_spider_request_latency_seconds{spider}` (histogram)
  - `pem_parser_failures_total{parser,reason}`
  - `pem_pipeline_items_processed_total{stage,outcome}`
  - `pem_dedup_hits_total{kind}` (`exact`, `simhash_near`)
  - `pem_llm_fallback_invocations_total{reason}`
  - `pem_matches_total{profile,score_bucket}`
  - `pem_notifications_sent_total{channel,outcome}`

## Diferenciais técnicos (para portfólio SDET/QA)

Este projeto foi desenhado pensando em **demonstrar engenharia de qualidade**, não só
features. Pontos que serão úteis em portfólio:

1. **Contract tests** contra fontes reais que rodam *nightly*, não em PR — separa testes
   determinísticos (gates de merge) de testes flakey-by-nature (sinal de drift).
2. **Snapshot-based regression** — toda HTML/PDF baixada é arquivada (`infrastructure/storage`).
   Quando um parser falha, é possível **replay** contra o snapshot e debugar offline.
3. **Property-based testing** (`hypothesis`) sobre os normalizadores de data — extrator de
   prazo em português brasileiro é cheio de casos absurdos (`"até 30/02"`, `"31 de novembro"`).
4. **Circuit breaker + chaos test** — fixture que injeta 503 aleatórios para validar
   que o pipeline se auto-protege.
5. **Mutation testing** (`mutmut`, opcional v1.0) na camada de matching — onde precisão é crítica.
6. **Test pyramid honesto** — `tests/unit/` (rápido), `tests/integration/` (com PG/Redis),
   `tests/contracts/` (rede), `tests/e2e/` (pipeline inteiro com fixtures).
7. **CI strict** — fail em warnings, fail em coverage drop, fail em mypy issue, fail em ruff.
8. **ADRs** registrando decisões importantes com contexto, alternativas e consequências.

## Documentação adicional

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — arquitetura em profundidade
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — milestones técnicos
- [`docs/SCRAPING_STRATEGY.md`](docs/SCRAPING_STRATEGY.md) — anti-quebra e resiliência
- [`docs/adr/`](docs/adr/) — Architecture Decision Records

## Licença

MIT. Veja [LICENSE](LICENSE).
