import logging

import trafilatura

from app.config import get_settings


logger = logging.getLogger(__name__)

_OPENAI_PROMPT = (
    "Extract the main article text from the following HTML as clean Markdown. "
    "Remove navigation, ads, sidebar. Return only the Markdown."
)


async def extract_content(html: str, url: str) -> dict[str, str]:
    """Extract AI-ready Markdown and a title from HTML.

    trafilatura performs deterministic main-content extraction. When it returns
    too little text (below ``cleaner_min_chars``) the HTML is handed to GPT-3.5
    as a fallback. Returns a dict with ``content`` and ``title`` keys.
    """

    settings = get_settings()
    title = _extract_title(html)

    content = trafilatura.extract(
        html,
        url=url,
        output_format="markdown",
        include_comments=False,
        include_tables=True,
    )
    if content and len(content.strip()) >= settings.cleaner_min_chars:
        return {"content": content.strip(), "title": title}

    fallback = await _fallback_with_openai(html, url)
    resolved = fallback.strip() if fallback else (content or "").strip()
    return {"content": resolved, "title": title}


def _extract_title(html: str) -> str:
    """Best-effort page title via trafilatura metadata."""

    try:
        metadata = trafilatura.extract_metadata(html)
    except Exception as exc:  # noqa: BLE001 - metadata parsing is best-effort
        logger.debug("Title extraction failed: %s", exc)
        return ""
    return (metadata.title or "").strip() if metadata else ""


async def _fallback_with_openai(html: str, url: str) -> str:
    """Use GPT-3.5 as a last resort when deterministic extraction is too thin."""

    settings = get_settings()
    if not settings.openai_api_key:
        logger.info("OpenAI fallback skipped because OPENAI_API_KEY is not set")
        return ""

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model=settings.openai_model,
            temperature=0,
            messages=[
                {"role": "system", "content": _OPENAI_PROMPT},
                {
                    "role": "user",
                    "content": f"URL: {url}\n\nHTML:\n{html[:120000]}",
                },
            ],
        )
        return response.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001 - external API failures must not 500
        logger.warning("OpenAI fallback failed: %s", exc)
        return ""
