# ADR-0007 — Matching precision-first

**Status**: Aceito
**Data**: 2026-05-10

## Contexto

O usuário recebeu o sistema para **evitar checagem manual de centenas de portais**. A pior
falha do sistema, do ponto de vista do usuário, é **enviar emails diários cheios de editais
irrelevantes**. Isso treina o usuário a ignorar o digest.

Perder um edital relevante é ruim, mas o usuário ainda pode checar manualmente as fontes
principais. Notificar lixo destrói o produto.

Portanto: **precision >> recall**.

## Decisão

Matching engine com **hard filters + soft score com threshold alto** (default 0.70):

### Hard filters (eliminatórios)

Qualquer um falso → descarta:
- `edital.is_gratuito == true`
- `edital.ies` está na whitelist e-MEC (ADR-0006)
- `edital.nivel` está em `profile.niveis_aceitos`
- `edital.modalidade` está em `profile.modalidades_aceitas`

### Soft score

Para cada `area_alvo` no perfil:
- `modo: exact` → soma `peso` se `edital.area_cnpq == alvo.codigo_cnpq`
- `modo: cross_discipline` → soma `peso * fator` se `alvo` aceita a formação do subscriber.
  Requer flag explícita no edital (ou heurística forte) — não match por "vaga similaridade".

Score final = sum(contributions). Notifica se `score ≥ score_minimo` (default 0.70).

### Logs de explanação

Cada match (positivo ou negativo) loga **a explicação**:
- quais hard filters passaram/falharam
- quais áreas contribuíram para o score
- score final

Isso vira `MatchRecord.explanation_json` no DB — auditável.

## Alternativas consideradas

1. **Recall-first com threshold baixo** — explode a caixa de email do usuário
2. **ML classifier** (embeddings + similarity) — não-determinístico, difícil explicar match
3. **Sem matching, mostrar tudo via API** — usuário precisa abrir API manualmente, perde o
   valor do digest automático

## Consequências

- ✅ Email do usuário só tem editais que de fato interessam
- ✅ Decisão de match é explicável e debugável
- ✅ Threshold ajustável sem mudar código
- ⚠️ Pode perder editais marginais (área correlata mas não exata) — aceito por design
- ⚠️ Requer cadastro CNPq de áreas correto — usar tabela oficial atualizada
