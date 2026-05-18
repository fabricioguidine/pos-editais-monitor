# Estratégia de scraping — resiliência e ética

## Filosofia

> Sites do governo brasileiro **mudam**. Eles mudam de URL, mudam de tema WordPress, mudam de
> CMS, mudam de servidor. Eles ficam fora do ar. Eles servem PDF onde antes serviam HTML. A
> pergunta não é "como construir um spider que nunca quebra" — é "como construir um sistema
> que detecta a quebra, alerta, e tem caminhos de degradação graciosa".

## Camadas de resiliência

### 1. Robots.txt (sempre)

Cada `HttpClient.get(url)` passa por `RobotsCheckerMiddleware`. O parser `protego` é cacheado
por host por 24h. Se o robots proíbe o user-agent, a requisição é abortada e logada — não há
override.

### 2. Rate limiter por host (Redis token bucket)

Implementado em Redis (token bucket atômico via Lua script) para funcionar **entre workers**.
Default: 0.5 RPS (1 req a cada 2s). Configurável por host via `PEM_RATE_LIMIT_OVERRIDES`.

### 3. Retry com backoff exponencial + jitter

`tenacity` com:
- 5 tentativas máximas
- backoff: `2 ** attempt` segundos + jitter 0-1s
- retry apenas para 5xx, 429, timeout, connection error
- 4xx (404, 403, 410) → **não retry** (sinaliza problema permanente)

### 4. Circuit breaker por host

Estado em Redis. Janela de 60s. Se 3 falhas → abre por 5 min. Em estado aberto, requests
falham imediatamente com `CircuitOpenError` e o pipeline marca o spider como `degraded`.
Half-open após o cooldown.

### 5. Cache de respostas

Resposta cacheada em Redis com TTL configurável por spider (default 6h). Spider pode
expirar manualmente. Reduz pressão sobre o upstream **e** acelera re-processamento local
durante desenvolvimento.

### 6. Fallback HTTP → Playwright

Se o conteúdo retornado por httpx é "vazio" (heurística: < 500 bytes ou ratio de tags < 0.3),
o spider pode optar por re-fetch com Playwright. Isso permite cobrir SPAs sem pagar o custo
de Playwright para o caso geral.

### 7. Snapshot imutável

Toda resposta crua é salva em `storage/snapshots/<spider>/<yyyy-mm-dd>/<sha256>.{html,pdf}`.
Isto permite:
- replay offline durante debug
- contract tests com payloads reais
- auditoria ("por que classificou assim?")

### 8. Parser confidence + LLM fallback

Cada parser retorna `(ParsedEdital, confidence: float)`. Se confidence < 0.65, o pipeline
invoca o LLM fallback. O resultado é comparado: se o LLM contradiz fortemente o rules-based,
o item vai para dead-letter queue para inspeção manual.

## Estratégia anti-quebra para sites universitários

Sites de universidades federais têm patterns que se repetem. Estes são os mais comuns e
como lidamos:

### Pattern 1: WordPress + tema custom

A maioria dos PPGs usa WordPress. Características:
- `<article class="post">` com conteúdo
- categorias/tags em `<a rel="category tag">`
- PDFs anexados como `<a href="...wp-content/uploads/.../edital.pdf">`

Parser: `parsers/wordpress/wp_parser.py` extrai com seletores resilientes a mudanças de
classe CSS (busca por padrão semântico, não por classe).

### Pattern 2: SIGAA

UFRN, UFPB, UFC e dezenas de outras usam SIGAA. Características:
- URLs estilo `/sigaa/public/programa/processo_seletivo.jsf`
- requer JSESSIONID — Playwright ou httpx com cookie jar
- tabelas HTML com `<table summary="...">`
- PDFs servidos com `Content-Disposition`

Parser: `parsers/sigaa/sigaa_parser.py` dedicado, com seletores XPath específicos.

### Pattern 3: Página estática institucional

Páginas em `/pos-graduacao/editais` puramente estáticas. HTML pequeno e simples.

Parser: `parsers/html/generic.py` com heurísticas + LLM fallback se nada bate.

### Pattern 4: PDF apenas (sem HTML)

Caso mais difícil. PDF muitas vezes é:
- escaneado (precisa OCR — fora do MVP)
- com colunas, headers/footers ruidosos
- com tabelas mal formatadas

Parser: `parsers/pdf/pdf_parser.py` usa `pdfplumber` para extrair layout, normaliza, tenta
rules. Confidence baixa → `parsers/pdf/llm_fallback.py` envia o texto para Claude com prompt
estruturado.

## Detecção de quebra (drift detection)

Cada spider tem **assertions de contrato** sobre a resposta bruta:

```python
class CapesSpider(BaseSpider):
    contract = {
        "min_links": 5,           # esperamos pelo menos 5 links de edital na listagem
        "must_contain": ["edital", "chamada"],
        "max_size_bytes": 5_000_000,
    }
```

Se contrato falha:
- log estruturado com severidade `WARNING`
- métrica `pem_spider_contract_violations_total{spider}` incrementa
- alerta se 3 violações em 1h

Contract tests **nightly** em CI rodam contra os sites reais e falham o build se contrato
viola — sinal precoce de drift.

## Estratégia de PDF

Sequência tentada por `parsers/pdf/pdf_parser.py`:

1. `pdfplumber.extract_text()` por página
2. Heurísticas de header/footer (linhas repetidas → descartar)
3. Detecção de seções via regex (`r"^\d+\.\s+\w"` para numeração)
4. Extração de:
   - Título (geralmente primeira linha em caixa alta após "EDITAL Nº ...")
   - Cronograma (tabela ou lista de datas)
   - Vagas (regex `\d+\s+vagas?`)
   - Modalidade (presencial / EAD / semipresencial)
   - Área de concentração
5. Se OCR-needed (texto extraído < 100 chars) → marca `needs_ocr=true`, fora do MVP
6. Confidence calculada a partir de quantos campos foram extraídos com sucesso
7. Se confidence < threshold → LLM fallback

## LLM fallback (Claude Haiku 4.5)

Prompt estruturado pedindo JSON. Cache de prompt do Anthropic ativo (5min TTL). Custo
estimado MVP: ~10 fallbacks/dia × ~$0.001 = **$0.30/mês**.

Template do prompt em `parsers/pdf/llm_fallback.py`:

```
SYSTEM: Você é um extrator de campos estruturados de editais de pós-graduação brasileiros.
USER: Extraia os campos seguintes do texto abaixo. Retorne JSON estrito.
Campos: titulo, nivel, modalidade, area_concentracao, vagas, periodo_inscricao{de,ate},
  is_gratuito, ies, link_pdf.

Texto:
<<<
{texto_normalizado_2000_chars}
>>>
```

Validação Pydantic obrigatória na saída. Se falhar parse JSON → dead-letter queue.

## Snapshots e replay

```bash
pem replay --snapshot-id <sha>
```

Lê o snapshot do object store, roda o pipeline em modo `--dry-run --no-network`. Útil para:
- debugar regressão após mudança de parser
- bootstrap de testes (`tests/fixtures/html/` gerados a partir de snapshots reais)
- demonstrar comportamento em entrevistas

## Riscos residuais

| Risco                                     | Probabilidade | Mitigação                                   |
|-------------------------------------------|---------------|---------------------------------------------|
| Site adiciona Cloudflare bot challenge    | Baixa         | Detectar, alertar, parar; não burlar        |
| robots.txt proíbe nosso UA                | Média         | Respeitar, marcar fonte como off            |
| PDF escaneado vira maioria                | Baixa         | Adicionar OCR opt-in (v0.4)                 |
| LLM API down                              | Baixa         | Pipeline funciona sem fallback, só perde precision |
| Custo LLM explode                         | Baixa         | Threshold mais conservador + cap diário     |
