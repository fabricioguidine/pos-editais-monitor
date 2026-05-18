import pytest

from pos_editais_monitor.parsers.wordpress.wp_parser import WordPressParser
from pos_editais_monitor.scraping.types import RawResponse

_SAMPLE_HTML = """<!doctype html>
<html><head>
  <meta name="generator" content="WordPress 6.4">
  <title>Edital 02/2026 PPGCC</title>
</head>
<body>
  <article>
    <h1 class="entry-title">Edital 02/2026 - Mestrado em Ciencia da Computacao</h1>
    <div class="entry-content">
      <p>O PPGCC abre processo seletivo para o Mestrado.</p>
      <p>Inscricoes: de 01/03/2026 a 15/04/2026. 20 vagas. Curso gratuito.</p>
      <p>Modalidade presencial.</p>
      <p><a href="https://www.example.com/wp-content/uploads/2026/edital.pdf">Baixar edital PDF</a></p>
    </div>
  </article>
</body></html>
""".encode("utf-8")


@pytest.mark.asyncio
async def test_wordpress_parser_extracts_fields() -> None:
    raw = RawResponse(
        url="https://www.example.com/ppgcc/editais/02-2026",
        final_url="https://www.example.com/ppgcc/editais/02-2026",
        status=200,
        headers={"content-type": "text/html; charset=utf-8"},
        body=_SAMPLE_HTML,
        spider="ufrgs-ppg",
    )
    parser = WordPressParser()
    assert parser.can_handle(raw)
    result = await parser.parse(raw)
    e = result.edital
    assert "Mestrado" in e.titulo
    assert e.url_pdf == "https://www.example.com/wp-content/uploads/2026/edital.pdf"
    assert e.periodo_inscricao is not None
    assert e.periodo_inscricao.ate is not None
    assert e.confidence > 0.5
