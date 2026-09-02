import logging
from typing import List, Tuple, Optional
import httpx
import trafilatura
from sqlalchemy.orm import Session

from app import models

logger = logging.getLogger(__name__)

# Core phrases indicating we hit a JavaScript shell or bot wall instead of the article
BLOCKLIST_PHRASES = [
    "you need to enable javascript to run the retriever portal",
    "please enable javascript to continue",
    "enable javascript and cookies to continue",
    "checking your browser before accessing",
]


def _passes_sanity_check(text: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Validates extracted text against known WAF and SPA shell patterns.
    """
    if not text:
        return False, "Extraction failed: No readable text found on page"

    text_clean = text.strip()
    if len(text_clean) < 15:
        return False, f"Sanity check failed: Text abnormally short ({len(text_clean)} chars)"

    text_lower = text_clean.lower()
    for phrase in BLOCKLIST_PHRASES:
        if phrase in text_lower:
            return False, f"Sanity check failed: Hit JS/WAF wall ('{phrase[:20]}...')"

    return True, None


def scrape_urls(db: Session, items_to_scrape: List[models.MediaPublication]) -> int:
    """
    Batch extracts standard web articles.
    Problematic links (like Retriever SPAs) are routed to manual review.
    """
    if not items_to_scrape:
        return 0

    processed_count = 0

    # Impersonate a standard Windows Chrome user
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,sv;q=0.8",
    }

    # 15.0 seconds explicit timeout prevents hanging on dead links
    timeout = httpx.Timeout(15.0)

    # Use a persistent HTTP/2 client session for connection pooling and speed
    with httpx.Client(headers=headers, timeout=timeout, follow_redirects=True, http2=True) as client:

        for item in items_to_scrape:
            if not item.content_url:
                item.has_processing_error = True
                item.processing_error_msg = "Missing content URL"
                db.commit()
                continue

            try:
                # 1. Fetch HTML
                response = client.get(item.content_url)
                response.raise_for_status()

                # 2. Extract Text
                extracted_text = trafilatura.extract(response.text)

                # 3. Sanity Check against WAF/JS Shells
                is_valid, error_msg = _passes_sanity_check(extracted_text)

                if not is_valid:
                    # Route to Case C (Manual Quarantine)
                    item.has_processing_error = True
                    item.processing_error_msg = error_msg
                else:
                    # Success
                    item.article_body = extracted_text.strip()
                    item.is_scraped = True
                    item.has_processing_error = False
                    item.processing_error_msg = None

            except httpx.HTTPError as e:
                item.has_processing_error = True
                item.processing_error_msg = f"HTTP request failed: {str(e)}"
            except Exception as e:
                item.has_processing_error = True
                item.processing_error_msg = f"Unexpected extraction error: {str(e)}"

            # Save state immediately for each item in the batch
            db.commit()
            processed_count += 1

    logger.info(f"Finished scraping batch. Processed {processed_count}/{len(items_to_scrape)} items.")
    return processed_count
