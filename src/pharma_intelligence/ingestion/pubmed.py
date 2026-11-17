from __future__ import annotations

import time
import xml.etree.ElementTree as ET
from typing import Any

import requests

from pharma_intelligence.config import settings
from pharma_intelligence.ingestion.common import SourceError, save_raw_text, session
from pharma_intelligence.models import EvidenceDocument


BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _params(extra: dict[str, Any]) -> dict[str, Any]:
    params = dict(extra)
    if settings.ncbi_email:
        params["email"] = settings.ncbi_email
    if settings.ncbi_api_key:
        params["api_key"] = settings.ncbi_api_key
    return params


def _request(client: requests.Session, endpoint: str, params: dict[str, Any]) -> str:
    try:
        response = client.get(f"{BASE_URL}/{endpoint}", params=_params(params), timeout=settings.request_timeout_seconds)
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        raise SourceError(f"PubMed E-utilities request failed: {exc}") from exc


def _node_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return " ".join("".join(node.itertext()).split())


def parse_fetch_xml(fetch_xml: str, drug_name: str) -> list[EvidenceDocument]:
    try:
        root = ET.fromstring(fetch_xml)
    except ET.ParseError as exc:
        raise SourceError("PubMed EFetch returned malformed XML") from exc
    documents: list[EvidenceDocument] = []
    for article in root.findall(".//PubmedArticle"):
        citation = article.find(".//MedlineCitation")
        pmid = _node_text(citation.find("PMID") if citation is not None else None)
        article_node = article.find(".//Article")
        if not pmid or article_node is None:
            continue
        title = _node_text(article_node.find("ArticleTitle")) or f"PubMed record {pmid}"
        abstracts = [_node_text(part) for part in article_node.findall(".//Abstract/AbstractText") if _node_text(part)]
        pub_date = article_node.find(".//JournalIssue/PubDate")
        date_text = "-".join(
            _node_text(pub_date.find(field)) for field in ("Year", "Month", "Day")
            if pub_date is not None and pub_date.find(field) is not None
        )
        journal = _node_text(article_node.find(".//Journal/Title"))
        content = "\n".join([title, f"Journal: {journal}" if journal else "", *abstracts]).strip()
        documents.append(EvidenceDocument(
            source="pubmed", external_id=pmid, title=title, text=content,
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/", drug_name=drug_name,
            published_at=date_text or None, metadata={"pmid": pmid, "journal": journal},
        ))
    return documents


def fetch_publications(drug_name: str, limit: int | None = None) -> list[EvidenceDocument]:
    client = session()
    max_results = min(limit or settings.max_results_per_source, 100)
    search_xml = _request(client, "esearch.fcgi", {
        "db": "pubmed", "term": f'"{drug_name}"[Title/Abstract]', "retmax": max_results,
        "retmode": "xml", "sort": "relevance",
    })
    save_raw_text("pubmed", drug_name, "esearch", search_xml)
    try:
        id_list = [node.text for node in ET.fromstring(search_xml).findall(".//IdList/Id") if node.text]
    except ET.ParseError as exc:
        raise SourceError("PubMed ESearch returned malformed XML") from exc
    if not id_list:
        return []
    # NCBI recommends spacing requests; one bounded EFetch batch keeps this client gentle.
    time.sleep(0.34)
    fetch_xml = _request(client, "efetch.fcgi", {
        "db": "pubmed", "id": ",".join(id_list), "retmode": "xml",
    })
    save_raw_text("pubmed", drug_name, "efetch", fetch_xml)
    return parse_fetch_xml(fetch_xml, drug_name)

