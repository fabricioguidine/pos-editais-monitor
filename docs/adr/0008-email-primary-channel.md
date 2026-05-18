# ADR-0008 — Email como canal primário de notificação

**Status**: Aceito
**Data**: 2026-05-10

## Contexto

O usuário expressou preferência clara: **digest diário por email** para
`fabricioguidine@gmail.com`, **apenas quando houver matches**. Telegram é opcional/secundário.

## Decisão

1. **Email é o canal default e sempre habilitado.** Configurado via SMTP (Gmail App Password).
2. **Digest único diário** às `07:00` (configurável via cron). Não há notificação por evento.
3. **Não enviamos email se o ciclo do dia não produziu matches** (flag `PEM_NOTIFY_ONLY_ON_MATCH=true`).
4. Template **Jinja2** em `notifications/templates/digest.html.j2` com:
   - cabeçalho com data
   - agrupamento por nível (mestrado, doutorado, etc.)
   - cada edital: título, IES, prazo, link para detalhe, link original
   - score do match e área que contribuiu
   - rodapé com link para "ajustar perfil" (API)
5. Telegram fica como canal opcional via `PEM_TELEGRAM_ENABLED=true`.
6. SMTP usa `aiosmtplib` (async) com TLS. Em desenvolvimento, o Docker Compose sobe
   `smtp4dev` — interface web em `http://localhost:5000` para inspeção sem mandar email
   de verdade.

## Alternativas consideradas

1. **Telegram primário** — depende de bot, conta, app. Email é universal.
2. **Notificação por evento (não digest)** — múltiplos emails/dia, fica spam
3. **Webhook genérico (Slack/Discord)** — útil em v0.4, não no MVP

## Consequências

- ✅ Canal universal, baixa fricção
- ✅ Digest agrupado evita ruído
- ✅ Zero notificação quando não há nada → confiança no sistema
- ⚠️ Gmail exige App Password (2FA obrigatório) — documentado no README
- ⚠️ Caso SMTP falhe, matches ainda ficam persistidos no DB (não se perdem) e podem ser
   re-enviados via `pem dispatch-digest --since=2026-05-09`
