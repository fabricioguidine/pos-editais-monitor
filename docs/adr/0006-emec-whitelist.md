# ADR-0006 — e-MEC como whitelist obrigatória de IES

**Status**: Aceito
**Data**: 2026-05-10

## Contexto

Há centenas de instituições oferecendo "pós-graduação" no Brasil, incluindo:
- IES públicas legítimas (federais, estaduais, IFs)
- IES privadas pagas
- "Pós-graduações" não reconhecidas pelo MEC
- Empresas de educação não credenciadas

O usuário **só quer pós gratuitas em IES públicas reconhecidas**. Filtrar isso ad-hoc por
nome é frágil — sufixos como "Faculdade Federal" podem aparecer em sites não confiáveis.

## Decisão

Usar o **cadastro oficial e-MEC** (`https://emec.mec.gov.br`) como **whitelist obrigatória**:

1. Pipeline mantém uma lista cacheada (TTL 7 dias) de IES com:
   - `situacao_cadastral = ATIVA`
   - `categoria_administrativa ∈ {Pública Federal, Pública Estadual, Pública Municipal, Especial}` ou IF/CEFET
   - `gratuita = true` (não cobra mensalidade)

2. Stage `match` do pipeline rejeita editais cujo `ies` não está na whitelist.

3. CLI `pem refresh-emec` força refresh manual.

4. Se e-MEC está fora do ar e cache expirou, **usamos o cache antigo** (degradação graciosa)
   com warning. Não falhamos o pipeline.

## Alternativas consideradas

1. **Whitelist hardcoded** — frágil, requer manutenção manual a cada nova IES
2. **Heurística por nome** ("Universidade Federal de X") — falsos positivos/negativos
3. **Sem whitelist** — notificaria editais privados pagos, contrário ao requisito

## Consequências

- ✅ Garante que só IES gratuitas reconhecidas pelo MEC sejam consideradas
- ✅ Lista atualiza automaticamente a cada 7 dias
- ✅ Resiliente a downtime do e-MEC (cache)
- ⚠️ e-MEC tem layout que muda — spider próprio precisa contract tests
- ⚠️ Categorização administrativa do e-MEC não é 100% confiável — pode haver borderline
   (IES estadual gratuita listada errada) — mitigado por overrides em `data/emec_overrides.yml`
