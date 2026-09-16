import asyncio

import httpx

from app.config import load_settings
from app.domain.web import HtmlCandidate
from app.services.html_retriever import HtmlRetriever


URL = (
    "https://ameriabank.am/en/personal/loans/"
    "mortgage/secondary-market"
)


async def main() -> None:
    settings = load_settings().http

    async with httpx.AsyncClient() as client:
        page = await HtmlRetriever(client, settings).retrieve(
            HtmlCandidate(url=URL)
        )

    print("Title:", page.title)
    print("Language:", page.language_hint)
    print("Final URL:", page.final_url)
    print("Canonical URL:", page.canonical_url)
    print("SHA-256:", page.sha256)
    print("Size:", page.size_bytes)
    print("\nHeadings:")
    for heading in page.headings:
        print(f"  H{heading.level}: {heading.text}")

    print("\nExtracted links:")
    for link in page.links:
        print(f"  {link.kind}: {link.text} -> {link.url}")

    print("\nMain text preview:")
    print(page.main_text[:1500])


asyncio.run(main())