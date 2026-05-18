# Roadmap — pos-editais-monitor

Milestones técnicos. Cada milestone tem **definition of done** explícita.

---

## v0.1 — MVP vertical funcional (em construção)

**Objetivo**: pipeline ponta a ponta rodando localmente com 2 fontes reais. Demonstra a
arquitetura sem precisar "fingir".

**DoD**:
- [ ] `make compose-up && make migrate && make run-worker` produz editais persistidos em ≤ 10min
- [ ] **DOU API** ingerindo editais publicados
- [ ] **Sucupira** cacheando catálogo de PPGs em CC (1.03) e Geociências (1.07)
- [ ] **e-MEC** whitelist cacheada e aplicada como gate
- [ ] RSS-first auto-detect quando spider encontrar `/feed/` ativo
- [ ] Dedup (canonical hash + simhash) com testes de unidade
- [ ] Classifier rules + Claude fallback (configurável)
- [ ] Match engine com perfil seed (fabricio) carregado via fixture
- [ ] Email digest enviado via SMTP — testado contra `smtp4dev` no compose
- [ ] FastAPI: `GET /v1/editais` paginado + `/healthz` + `/metrics`
- [ ] CLI: `pem scrape`, `pem worker`, `pem dispatch-digest`, `pem refresh-emec`
- [ ] Docker compose: postgres + redis + smtp4dev + app + worker
- [ ] CI: lint + mypy strict + unit tests, coverage ≥ 75%
- [ ] Documentação: README, ARCHITECTURE, 8 ADRs, SCRAPING_STRATEGY

---

## v0.2 — Expansão de fontes + observabilidade

**Objetivo**: cobrir as fontes pesadas (SIGAA federado, WordPress PPGs com RSS, UAB) e ter
visibilidade operacional.

**DoD**:
- [ ] **SIGAA spider genérico** (Playwright) cobrindo 40+ IES via lista de subdomínios
- [ ] **WordPress PPG spider** com RSS-first detection
- [ ] UAB spider
- [ ] UFRGS PPG como Tier 3 exemplo (showcase)
- [ ] Telegram channel funcionando (opcional)
- [ ] Prometheus + Grafana no compose com dashboard padrão
- [ ] OpenTelemetry exporter OTLP (Tempo/Jaeger no compose)
- [ ] Contract tests nightly em CI (job separado)
- [ ] Hypothesis property tests para extrator de datas
- [ ] Coverage ≥ 80%

---

## v0.3 — DOU + IFs + auto-cura

**Objetivo**: aumentar coverage e ganhar resiliência a mudanças de HTML.

**DoD**:
- [ ] DOU API integrada (filtra publicações pertinentes)
- [ ] 5 institutos federais no whitelist com spiders
- [ ] Auto-detection de seletor quebrado (diff DOM + alerta)
- [ ] LLM-assisted selector repair (best-effort, opt-in)
- [ ] Object store em MinIO (substitui filesystem local)
- [ ] Replay CLI: `pem replay --snapshot-id`

---

## v0.4 — Multi-subscriber + API pública

**Objetivo**: virar produto utilizável por mais gente.

**DoD**:
- [ ] Modelo multi-subscriber com OAuth (Google)
- [ ] Frontend mínimo (Next.js?) para gerenciar perfil
- [ ] Webhook outbound (Slack/Discord)
- [ ] Cliente TS gerado a partir do OpenAPI
- [ ] Quota de notificações por subscriber

---

## v1.0 — Produção

**Objetivo**: estado pronto para uso real e showcase de portfólio.

**DoD**:
- [ ] Dashboards Grafana completos (latência, taxa de match, custo LLM)
- [ ] Mutation testing (mutmut) na camada de matching com score > 80%
- [ ] Chaos test em pipeline (injeção de 5xx)
- [ ] Postmortem template + runbook
- [ ] Demo deployado (single VPS) ou caso de uso documentado
- [ ] Vídeo de 5min explicando arquitetura para portfólio
