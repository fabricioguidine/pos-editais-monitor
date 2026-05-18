# ADR-0001 — Clean Architecture com domínio puro

**Status**: Aceito
**Data**: 2026-05-10

## Contexto

O projeto precisa monitorar editais de fontes muito heterogêneas (HTML, PDF, SIGAA, APIs) e
notificar via canais diversos (email, telegram, webhook). A camada de I/O é volátil — sites
mudam, novos canais aparecem.

Sem isolamento, tendemos a ter regras de negócio (o que é um "edital válido", "como
classificar área", "quando notificar") espalhadas entre views FastAPI, models SQLAlchemy e
spiders. Isso impede testar a lógica de domínio sem subir DB/rede e fragiliza o sistema.

## Decisão

Adotar Clean Architecture (Hexagonal/Ports-and-Adapters) com camadas:

```
domain     →  apenas tipos puros (entidades, VOs, enums). Zero imports externos.
infrastructure → implementa portas: db, llm, smtp, emec, redis. Trocável.
application/use_cases → opcional v0.2 (por enquanto pipeline cumpre esse papel).
```

O domínio define **interfaces (Protocols)** que infraestrutura implementa. O pipeline depende
de Protocols, não de classes concretas — testes injetam fakes.

## Alternativas consideradas

1. **Anemic domain + active record** — Models SQLAlchemy carregariam lógica.
   - Pro: menos boilerplate
   - Contra: testes de regras de negócio precisam de DB; refactor caro

2. **Hexagonal estrito com use cases** — uma classe por caso de uso.
   - Pro: máximo isolamento, ideal para times grandes
   - Contra: overkill para o tamanho atual; muito boilerplate

## Consequências

- ✅ Domínio testável sem PG/Redis/rede
- ✅ Troca de Postgres por outro backend não toca domínio
- ✅ Pipeline orquestra Protocols, não implementações
- ⚠️ Mapeamento entre `ORM Edital` e `domain Edital` requer conversores
- ⚠️ Custo cognitivo levemente maior para quem chega ao projeto
