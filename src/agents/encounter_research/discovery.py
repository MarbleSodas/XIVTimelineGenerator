"""Guide discovery helpers for encounter research."""

from __future__ import annotations

from collections import OrderedDict
from typing import Iterable

from .models import SearchResult, SourceDocument
from .open_websearch_client import OpenWebSearchClient

GUIDE_SITES = {
    "icy-veins": "icy-veins.com",
    "hardcore-gamer": "hardcoregamer.com",
}


def build_queries(encounter: dict[str, str]) -> dict[str, list[str]]:
    code = encounter.get("code", "")
    full_name = encounter.get("full_name", "")
    boss_name = encounter.get("boss_name", "")
    queries: dict[str, list[str]] = {}
    for site, domain in GUIDE_SITES.items():
        queries[site] = [
            f'site:{domain} "{code}" "{full_name}" "{boss_name}" FFXIV guide',
            f'site:{domain} "{boss_name}" "{full_name}" mechanics',
        ]
    return queries


def discover_guide_documents(
    encounter: dict[str, str],
    client: OpenWebSearchClient,
    *,
    limit_per_query: int = 3,
    max_chars: int = 30000,
) -> tuple[list[SearchResult], list[SourceDocument]]:
    deduped_results: "OrderedDict[str, SearchResult]" = OrderedDict()
    for site, queries in build_queries(encounter).items():
        for query in queries:
            for result in client.search(query, limit=limit_per_query):
                if _belongs_to_site(result.url, site):
                    deduped_results.setdefault(result.url, result)

    documents: list[SourceDocument] = []
    for result in deduped_results.values():
        document = client.fetch_web_content(result.url, max_chars=max_chars)
        title = document.title or result.title
        documents.append(
            SourceDocument(
                site=document.site,
                url=document.url,
                final_url=document.final_url,
                title=title,
                content=document.content,
                content_type=document.content_type,
                truncated=document.truncated,
            )
        )

    return list(deduped_results.values()), documents


def unique_sites(documents: Iterable[SourceDocument]) -> list[str]:
    sites = OrderedDict()
    for document in documents:
        sites.setdefault(document.site, None)
    return list(sites.keys())


def _belongs_to_site(url: str, site: str) -> bool:
    domain = GUIDE_SITES.get(site, "")
    return domain in url.lower()
