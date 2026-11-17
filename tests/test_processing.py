from pharma_intelligence.models import EvidenceDocument
from pharma_intelligence.processing.chunking import chunk_text
from pharma_intelligence.processing.document_parser import clean_text
from pharma_intelligence.processing.metadata import normalize_document


def test_parser_removes_markup_and_keeps_paragraphs():
    assert clean_text("<p>A &amp; B</p>\n<p>Second</p>") == "A & B\nSecond"


def test_chunk_boundaries_keep_words_and_overlap():
    chunks = chunk_text("alpha beta gamma delta epsilon zeta", chunk_size=18, overlap=5)
    assert len(chunks) > 1
    assert all(len(chunk) <= 18 for chunk in chunks)
    assert "alpha" in chunks[0]
    assert set(" ".join(chunks).split()) == {"alpha", "beta", "gamma", "delta", "epsilon", "zeta"}
    assert set(chunks[0].split()) & set(chunks[1].split())


def test_empty_and_invalid_chunks():
    assert chunk_text("   ") == []
    try:
        chunk_text("a", chunk_size=10, overlap=10)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid overlap should raise")


def test_missing_source_fields_are_rejected():
    doc = EvidenceDocument(source="pubmed", external_id="1", title="", text="text", url="https://pubmed.ncbi.nlm.nih.gov/1/")
    try:
        normalize_document(doc)
    except ValueError:
        pass
    else:
        raise AssertionError("missing title should raise")


def test_incorrect_metadata_type_is_rejected():
    doc = EvidenceDocument(source="pubmed", external_id="1", title="Title", text="text", url="https://pubmed.ncbi.nlm.nih.gov/1/")
    doc.metadata = []
    try:
        normalize_document(doc)
    except ValueError:
        pass
    else:
        raise AssertionError("non-object metadata should raise")
