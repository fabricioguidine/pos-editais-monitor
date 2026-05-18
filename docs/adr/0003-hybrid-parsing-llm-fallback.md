# ADR-0003 — Parsing híbrido: rules first, LLM como fallback

**Status**: Aceito
**Data**: 2026-05-10

## Contexto

Editais brasileiros têm formatos extremamente variados:
- HTML estático com tabelas → parsing trivial
- WordPress com tema custom → médio
- SIGAA → estruturado mas requer Playwright
- PDF de 20 páginas com layout caótico → muito difícil

Parser puramente rules-based ganha em custo, latência, e determinismo, mas falha em casos
caóticos. Parser puramente LLM ganha em flexibilidade mas tem custo por chamada e latência.

## Decisão

Adotar pipeline híbrido:

1. **Rules sempre tentado primeiro** — barato, rápido, testável
2. Cada parser retorna `(ParsedEdital, confidence: float ∈ [0,1])`
3. Confidence é uma função do "quantos campos críticos foram extraídos com sucesso"
4. Se `confidence < PEM_LLM_CONFIDENCE_THRESHOLD` (default 0.65) → invoca LLM fallback
5. LLM (Claude Haiku 4.5) recebe texto normalizado, retorna JSON Pydantic-validado
6. Prompt caching do Anthropic ativo (5min TTL) reduz custo

Modelo escolhido: **Claude Haiku 4.5** — custo baixo, latência baixa, qualidade suficiente
para extração estruturada simples.

## Alternativas consideradas

1. **Rules puro** — abandonaria editais caóticos (perda de recall)
2. **LLM-first** — custo ~10x maior, latência alta, dependência forte de API externa
3. **Modelo local (llama.cpp)** — qualidade insuficiente para PT-BR em hardware comum

## Consequências

- ✅ Sistema funciona offline para a maioria dos casos (rules)
- ✅ Resiliente a HTML/PDF caótico via fallback
- ✅ Custo previsível e baixo (~$0.30/mês no MVP)
- ⚠️ Threshold de confidence requer tuning empírico
- ⚠️ Quando LLM e rules discordam fortemente, item vai para dead-letter (intervenção manual)
- ⚠️ Dependência externa (Anthropic API) — sistema continua funcionando sem ela, com menos precisão
