# Estratégia de fontes — onde achar editais

> Documento curatorial. Mantido atualizado conforme aprendemos com cada fonte real.

## Princípio

> Brasil tem ~7000 instituições de ensino superior cadastradas. Tentar scrapear todas é
> engenharia de cobertura, não de inteligência. **A estratégia certa é em camadas**:
> primeiro fontes oficiais centralizadas (alto sinal, baixo custo), depois federadores
> (1 parser → N IES), depois per-IES apenas onde o conteúdo é único e relevante ao perfil.

## Camadas

### Tier 1 — Fontes oficiais centralizadas (MVP)

| Fonte | URL | Papel | Mecanismo | Atualização |
|---|---|---|---|---|
| **DOU (Imprensa Nacional)** | `in.gov.br/leiturajornal` | Editais oficiais publicados (verdade legal) | API JSON pública | Diária (D-1) |
| **Plataforma Sucupira (CAPES)** | `sucupira.capes.gov.br` | Catálogo de PPGs reconhecidos + área CNPq + IES | HTTP estático | Trimestral |
| **e-MEC** | `emec.mec.gov.br` | Whitelist de IES públicas e gratuitas | HTTP + cache 7d | Mensal |

**Por que esses três**:
- **DOU**: tem força legal. Todo edital de IES federal acaba aqui. API pública = determinismo.
- **Sucupira**: dá a lista *correta* de PPGs ativos com classificação CNPq. Sem ela, não
  conseguiríamos filtrar editais "em CC" ou "em Geociências" de forma confiável.
- **e-MEC**: filtra ruído. Sem ela, processaríamos editais de IES privadas pagas.

### Tier 2 — Federadores por sistema (Sprint 2)

Quando uma única classe de parser serve muitas IES.

| Sistema | Cobertura | URL padrão |
|---|---|---|
| **SIGAA** | UFRN, UFPB, UFC, UFCG, UFMA, UFES, UFV, UFRPE, UFOPA, UFAM, IFCE, IFRN + ~30 outras | `https://sigaa.<ies>.br/sigaa/public/programa/processo_seletivo.jsf` |
| **SIE/SIPAC** | UFSM, UFSC (parcial) | varia |
| **WordPress + tema PPG** | Maioria das outras IFES e IFs | `https://www.<ies>.br/<sigla-ppg>/` |

ROI: 1 implementação de parser SIGAA = 40+ IES cobertas.

### Tier 3 — Per-IES individual (Sprint 3+)

Spider dedicado apenas para:
- IES com PPG **na área do subscriber** **E**
- IES que **não está em SIGAA/WordPress padrão**

Para o subscriber `fabricio` (CC + Geociências), Tier 3 prioritário:
- USP (ciência da computação ICMC, geociências IGc)
- Unicamp (IC, IG)
- UFRGS (INF, IGEO)
- UFMG (DCC, IGC)
- UFRJ (PESC/COPPE, IGEO)
- UFSC (INE, GCN)

## Sinais complementares (descoberta, não conteúdo)

- **RSS feeds** (`<wp-base>/feed/`): a maioria dos WordPress de PPG mantém RSS ativo. **A pipeline
  testa RSS antes de scrapear HTML** — economiza requests e é mais resiliente.
- **Sitemaps** (`sitemap.xml`): diff diário para detectar URLs novas.
- **Twitter/X institucional** (`@CAPES_oficial`, `@MEC_Comunicacao`): apenas como **gatilho**
  de prioridade em uma fila — não é fonte do conteúdo.

## Antipatterns evitados

1. **Scrapear "todas as universidades"** — engenharia de cobertura, não de relevância.
2. **Confiar em fonte única** — CAPES Sucupira tem latência; IES publica antes. Dedup unifica.
3. **Ignorar RSS** — perder requests grátis quando o site oferece feed estruturado.
4. **Spider para IES não-whitelist** — e-MEC eliminatório por design.

## Política de inclusão de nova fonte

Antes de criar um spider novo:

1. A fonte tem pelo menos 1 PPG na área de algum subscriber ativo? Não → reject.
2. A IES da fonte está na whitelist e-MEC? Não → reject.
3. A fonte é coberta indiretamente por DOU/Sucupira com latência aceitável? Sim → defer.
4. A fonte expõe API/RSS/sitemap? Sim → spider barato. Não → avaliar custo de manutenção.

Se passar nas 4 perguntas, abrir ADR de fonte (`docs/adr/sources/`) e implementar.
