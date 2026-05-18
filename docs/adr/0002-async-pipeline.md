# ADR-0002 — Pipeline async com asyncio.Queue (sem Celery/RabbitMQ no MVP)

**Status**: Aceito
**Data**: 2026-05-10

## Contexto

Precisamos processar fetch→parse→dedup→classify→persist→match→notify de forma concorrente.
As escolhas óbvias para sistemas Python de scraping são:

1. Celery + RabbitMQ/Redis broker
2. Scrapy + ItemPipeline
3. Pipeline custom async com `asyncio.Queue`
4. Prefect/Dagster

## Decisão

Para o MVP, usar **pipeline async custom com `asyncio.Queue` entre stages** dentro de um
processo worker único. APScheduler dispara jobs periódicos.

Razões:
- Operação **single-host** (Docker Compose local) — não precisamos de broker distribuído
- Volume baixo (~80 URLs/dia × poucos editais → ~200 items/dia)
- Cada stage é I/O-bound — async é ideal
- Zero infraestrutura extra além de PG + Redis (já necessários)
- Migrar para Celery depois é uma camada de adapters; o pipeline em si não muda

## Alternativas consideradas

1. **Celery** — ótimo para escala, mas overkill agora. Requer broker, beat scheduler, workers
   separados. Mais yaml/config do que código.
2. **Scrapy** — feito para crawl, não para o pipeline pós-extração. Acopla demais.
3. **Prefect/Dagster** — excelente para data pipelines complexos. Curva alta. Adicionar em
   v1.0 se a complexidade crescer.

## Consequências

- ✅ MVP simples, único processo `pem worker` faz tudo
- ✅ Backpressure natural via `Queue(maxsize=...)`
- ✅ Tracing/logging end-to-end mais fácil
- ⚠️ Se um stage trava (deadlock async), todo o pipeline trava — mitigado por timeouts
- ⚠️ Escalar para múltiplos hosts requer migração futura para broker real

## Plano de migração (v0.4+)

Caso o sistema cresça, extrair stages "pesados" (LLM fallback, Playwright fetch) para
workers Celery separados. As filas internas viram filas remotas (Redis broker). O Protocol
de cada stage não muda — só a implementação do `enqueue`/`consume`.
