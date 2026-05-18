# ADR-0004 — Dedup: hash canônico + simhash

**Status**: Aceito
**Data**: 2026-05-10

## Contexto

Editais podem ser:
- republicados por mais de uma fonte (CAPES + portal da IES) — **mesmo edital**
- editados após publicação (correção de cronograma) — **mesmo edital, snapshot novo**
- republicados pelo mesmo portal com URL diferente — **mesmo edital, URL nova**

Precisamos identificar:
1. **Idempotência exata** — não recriar registro idêntico (hash exato)
2. **Quase-duplicatas** — variações cosméticas (espaços, ordem de campos)
3. **Atualizações** — mesmo edital, conteúdo mudou → novo snapshot

## Decisão

Camada dupla de hash:

### 1. Canonical hash (SHA-256)

Construído a partir de campos canônicos normalizados:
```
canonical = sha256(
  normalize(titulo) + "|" +
  normalize(ies) + "|" +
  nivel.value + "|" +
  periodo_inscricao.isoformat() + "|" +
  area_principal
)
```
`normalize`: NFKD, lowercase, remove acentos, colapsa espaços.

Detecta: republicação idêntica e idempotência.

### 2. Simhash de 64 bits

Sobre os tokens normalizados do conteúdo completo. Dois editais com **Hamming distance ≤ 3**
são considerados a mesma família.

Detecta: variações cosméticas, republicações em portais diferentes, edital reissued.

### 3. Change detection

Para mesmo `canonical_hash`, comparamos `simhash` do snapshot anterior:
- igual → nada a fazer
- ≤ 3 bits de diferença → atualização cosmética (loga, não notifica)
- > 3 bits → conteúdo material mudou → novo snapshot + evento `EditalAtualizadoEvent` →
  matchers consideram reenvio

## Alternativas consideradas

1. **Apenas SHA-256 do conteúdo bruto** — qualquer espaço em branco gera "novo edital"
2. **MinHash + LSH** — overkill para o volume; simhash é mais simples e suficiente
3. **Embeddings + cosine similarity** — caro, requer modelo, não-determinístico
4. **Comparação textual com `difflib`** — caro O(n*m), não escala

## Consequências

- ✅ Idempotência clara via canonical hash
- ✅ Detecta updates significativos via simhash threshold
- ✅ Tudo determinístico, testável, sem ML
- ⚠️ Threshold de 3 bits é empírico — pode requerer tuning
- ⚠️ Texto normalizado precisa ser cuidadoso (Unicode NFKD, removal de PDF artifacts)
