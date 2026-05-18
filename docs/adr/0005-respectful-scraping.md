# ADR-0005 — Scraping respeitoso e auditável

**Status**: Aceito
**Data**: 2026-05-10

## Contexto

Sites alvo são de **instituições públicas**. A informação é pública. Tecnicamente, scraping
agressivo (rotação de IPs, stealth, CAPTCHA solver) funcionaria. Mas:

- Sites do governo são lentos e mal financiados — agressividade prejudica usuários reais
- O projeto é portfólio público — práticas anti-éticas são reputacionalmente ruins
- Bloqueios de hosting/proxy seriam um problema operacional contínuo

## Decisão

Postura **respeitosa e auditável**:

1. **`robots.txt` é respeitado** sem override. Se proíbe, paramos.
2. **User-Agent identificável** com URL do projeto e email de contato:
   ```
   pos-editais-monitor/0.1 (+https://github.com/fabricioguidine/pos-editais-monitor; contact: fabricioguidine@gmail.com)
   ```
3. **Rate limit conservador**: 0.5 RPS por host por default.
4. **Sem rotação de proxies, sem stealth, sem solver.**
5. **Cache agressivo** em Redis para evitar re-fetch.
6. **Playwright apenas onde necessário** (SIGAA, sites JS-heavy). HTTP simples para o resto.
7. **Backoff exponencial + circuit breaker** — em caso de erro do upstream, recuamos.

Se um site proibir explicitamente, **damos baixa nele**, não tentamos contornar.

## Alternativas consideradas

1. **Full anti-bot stack** (rotação de proxy residencial, stealth, fingerprint) — funciona
   tecnicamente, mas:
   - eticamente questionável contra sites públicos
   - custo de operação (proxy pago)
   - péssimo para portfólio
2. **Stealth leve** (só rotação de UA) — não muda muito o custo/benefício
3. **Postura ainda mais restrita** (só fontes com API/RSS) — perda de coverage gigantesca

## Consequências

- ✅ Sistema é apresentável publicamente sem ressalvas éticas
- ✅ Probabilidade baixa de IP bloqueado
- ✅ Mais fácil pedir desbloqueio se for bloqueado (contato no UA)
- ⚠️ Coleta diária é lenta (~3min para CAPES) — não é problema com cron diário
- ⚠️ Sites com Cloudflare challenge → marcamos como off, não burlamos
