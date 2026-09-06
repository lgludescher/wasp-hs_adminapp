# app/services/swepub.py
import logging
import time
import re
from typing import List, Optional
from datetime import datetime
import httpx

from sqlalchemy.orm import Session

from app import crud, schemas

logger = logging.getLogger(__name__)

# Discovery API
SWEPUB_XSEARCH_URL = "http://libris.kb.se/xsearch"

# Bibliometrics API (Clean, deduplicated JSON-LD / BIBFRAME version)
SWEPUB_BIBLIOMETRICS_URL = "https://bibliometri.swepub.kb.se/api/v2/bibliometrics/publications"


def _build_researcher_chunks(db: Session, chunk_size: int = 12) -> List[str]:
    """Builds chunked queries for active researchers to avoid URI Too Long errors."""
    roles = crud.list_person_roles(db, active=True)

    unique_names = set()
    for pr in roles:
        if pr.person:
            first = pr.person.first_name.strip()
            last = pr.person.last_name.strip()
            if first and last:
                unique_names.add(f"{first} {last}")

    names_list = list(unique_names)
    chunks = []

    for i in range(0, len(names_list), chunk_size):
        chunk_names = names_list[i:i + chunk_size]
        query_parts = [f'author:"{name}"' for name in chunk_names]
        query_str = "(" + " OR ".join(query_parts) + ")"
        chunks.append(query_str)

    return chunks


def _fetch_swepub_xsearch(query_string: str) -> List[dict]:
    """Executes a paginated HTTP fetch against the Libris Xsearch API for discovery."""
    results = []
    start = 1
    n = 200

    with httpx.Client() as client:
        while True:
            params = {
                "database": "swepub",
                "format": "json",
                "query": query_string,
                "start": start,
                "n": n
            }
            try:
                response = client.get(SWEPUB_XSEARCH_URL, params=params, timeout=20.0)
                response.raise_for_status()
            except httpx.RequestError as e:
                logger.error(f"HTTP Request failed for SwePub query '{query_string}': {e}")
                break
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP Status error {e.response.status_code} for SwePub query: {e}")
                break

            data = response.json().get("xsearch", {})
            records_total = data.get("records", 0)
            items = data.get("list", [])

            if not items:
                break

            results.extend(items)

            start += n
            if start > records_total:
                break

            time.sleep(0.5)

    return results


def fetch_recent_publications(db: Session, since: Optional[datetime] = None) -> List[dict]:
    """Phase 1: Hybrid Fetch. Discovers via Xsearch, Upgrades via Bibliometrics API."""

    # 1. Date Margin Logic (1-year margin, hard floor at 2019)
    start_year = 2019
    if since:
        start_year = max(2019, since.year - 1)

    logger.info(f"Starting SwePub fetch. Target year >= {start_year}")

    xsearch_raw_data = []
    seen_ids = set()

    # 2. Add Source Tagging AND Python-based Year Filtering
    def _add_items(items: List[dict], source_tag: str):
        for item in items:
            # Safely extract the year published from the raw Xsearch data
            pub_year_raw = item.get("date") or item.get("year") or item.get("issued") or item.get("publication")
            if isinstance(pub_year_raw, list):
                pub_year_raw = pub_year_raw[0]

            item_year = 0
            if pub_year_raw:
                match = re.search(r'\b(19\d\d|20\d\d)\b', str(pub_year_raw))
                if match:
                    item_year = int(match.group(1))

            # Skip this item entirely if it's older than our floor
            if item_year > 0 and item_year < start_year:
                continue

            fallback_id = None
            identifiers = item.get("identifier", [])
            if isinstance(identifiers, str):
                identifiers = [identifiers]

            for ident in identifiers:
                if isinstance(ident, str) and ("oai:" in ident or "urn:" in ident):
                    fallback_id = ident
                    break

            if not fallback_id:
                fallback_id = str(item.get("title", "")).strip().lower()

            if fallback_id and fallback_id not in seen_ids:
                seen_ids.add(fallback_id)
                item["_fetch_source"] = source_tag  # Track why it was fetched
                item["_start_year"] = start_year  # Tag the date floor
                xsearch_raw_data.append(item)

    # 3. Expanded WASP-HS Query
    wasp_query = (
        '"WASP-HS" OR '
        '"Wallenberg AI, Autonomous Systems and Software program - Humanity and Society" OR '
        '"Wallenberg AI, Autonomous Systems and Software program – Humanities and Society"'
    )
    wasp_hs_items = _fetch_swepub_xsearch(wasp_query)
    _add_items(wasp_hs_items, source_tag="wasphs")
    logger.info(f"Phase 1a: Retrieved {len(wasp_hs_items)} raw records from standalone WASP-HS query.")

    # 4. Fetch researchers in chunked queries
    chunks = _build_researcher_chunks(db)
    author_items_count = 0
    for chunk in chunks:
        chunk_items = _fetch_swepub_xsearch(chunk)
        _add_items(chunk_items, source_tag="author")
        author_items_count += len(chunk_items)

    logger.info(f"Phase 1b: Retrieved {author_items_count} raw records across {len(chunks)} author queries.")
    logger.info(
        f"Phase 1c: Deduplicated & pre-filtered list down to {len(xsearch_raw_data)} target records for API upgrade.")

    # 5. Upgrade to Clean JSON-LD via Bibliometrics API
    final_data = []
    with httpx.Client(timeout=15.0) as client:
        for record in xsearch_raw_data:
            oai_id = None
            identifiers = record.get("identifier", [])
            if isinstance(identifiers, str):
                identifiers = [identifiers]

            for ident in identifiers:
                if isinstance(ident, str) and "oai:" in ident:
                    match = re.search(r'(oai:.*)', ident)
                    if match:
                        oai_id = match.group(1)
                        break

            if oai_id:
                try:
                    resp = client.get(f"{SWEPUB_BIBLIOMETRICS_URL}/{oai_id}")
                    if resp.status_code == 200:
                        clean_data = resp.json()
                        clean_data["_format"] = "bibframe"
                        clean_data["_fallback_id"] = oai_id
                        clean_data["_fetch_source"] = record.get("_fetch_source")  # Preserve tag!
                        clean_data["_start_year"] = record.get("_start_year") # Preserve year floor!
                        final_data.append(clean_data)
                        time.sleep(0.1)
                        continue
                except Exception as e:
                    logger.warning(f"Failed to fetch clean data for {oai_id}: {e}")

            record["_format"] = "xsearch"
            final_data.append(record)

    logger.info(f"Finished SwePub fetch. Total unique records retrieved: {len(final_data)}")

    bibframe_count = sum(1 for r in final_data if r.get("_format") == "bibframe")
    xsearch_fallback_count = len(final_data) - bibframe_count

    logger.info(
        f"Phase 2 Complete: Upgraded {bibframe_count} records to clean BIBFRAME JSON-LD. "
        f"Fell back to Xsearch parser for {xsearch_fallback_count} records."
    )

    return final_data


def _parse_bibframe(data: dict) -> dict:
    """Parses pristine BIBFRAME JSON-LD data exactly to KB's structural specifications."""
    record = data

    # 1. Root Record Extraction (Physical Instance)
    if "@graph" in data:
        for item in data["@graph"]:
            if item.get("@type") == "Instance":
                record = item
                break
        else:
            if data["@graph"]:
                record = data["@graph"][0]

    work = record.get("instanceOf", {})
    if isinstance(work, list) and work:
        work = work[0]

    swepub_id = record.get("@id") or data.get("_fallback_id")

    # 2. DOI Normalization
    doi = None
    for identifier in record.get("identifiedBy", []):
        if isinstance(identifier, dict) and identifier.get("@type") == "DOI":
            raw_doi = identifier.get("value", "")
            doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", raw_doi).strip()
            break

    # 3. Title & Subtitle Concatenation
    title = "Unknown Title"
    has_title_array = work.get("hasTitle", [])
    if isinstance(has_title_array, dict):
        has_title_array = [has_title_array]

    if has_title_array:
        title_obj = next((t for t in has_title_array if t.get("@type") == "Title"), has_title_array[0])
        main = title_obj.get("mainTitle", "").strip()
        sub = title_obj.get("subtitle", "").strip()

        if main and sub:
            if main.endswith(("-", "–", "—", ":", "?", "!")):
                title = f"{main} {sub}"
            else:
                title = f"{main}: {sub}"
        elif main:
            title = main

    # 4. Abstract Mapping
    abstract = None
    summary_data = work.get("summary", [])
    if isinstance(summary_data, list) and summary_data:
        abstract = summary_data[0].get("label")
    elif isinstance(summary_data, dict):
        abstract = summary_data.get("label")

    # 5. Clean Author Extraction (Ordered Fallback & Role Filtering)
    contributions = work.get("contribution", [])
    if isinstance(contributions, dict):
        contributions = [contributions]

    authors_list = []
    editors_list = []
    untagged_list = []

    for contribution in contributions:
        agent = contribution.get("agent", {})
        if not isinstance(agent, dict) or agent.get("@type") != "Person":
            continue

        roles = [r.get("@id", "") for r in contribution.get("role", []) if isinstance(r, dict)]

        # HARD EXCLUSIONS: Always ignore supervisors, opponents, funders, and organizations
        if any(r.endswith(('/ths', '/opn', '/org', '/fnd')) for r in roles):
            continue

        # Extract name cleanly
        given = agent.get("givenName", "")
        family = agent.get("familyName", "")
        name = agent.get("name", "")

        full_name = ""
        if given or family:
            full_name = f"{given} {family}".strip()
        elif name:
            full_name = name.strip()

        if not full_name:
            continue

        # BUCKETING
        if any(r.endswith("/aut") for r in roles):
            authors_list.append(full_name)
        elif any(r.endswith("/edt") for r in roles):
            editors_list.append(full_name)
        elif not roles:
            untagged_list.append(full_name)

    # RESOLUTION WATERFALL
    if authors_list:
        authors_raw = "; ".join(authors_list)
    elif editors_list:
        suffix = " (ed.)" if len(editors_list) == 1 else " (eds.)"
        authors_raw = "; ".join(editors_list) + suffix
    elif untagged_list:
        authors_raw = "; ".join(untagged_list)
    else:
        authors_raw = None

    # 6. Dates (Preprints & Theses Waterfall)
    published_year = None
    published_date = None

    publication = record.get("publication", [])
    if isinstance(publication, dict): publication = [publication]

    dissertation = record.get("dissertation", [])
    if isinstance(dissertation, dict): dissertation = [dissertation]

    provision = record.get("provisionActivity", [])
    if isinstance(provision, dict): provision = [provision]

    meta = record.get("meta", {})

    # Year resolution
    year_candidates = [
        next((p.get("date") for p in publication if p.get("date")), None),
        next((d.get("date") for d in dissertation if d.get("date")), None),
        meta.get("creationDate")
    ]
    for y_cand in year_candidates:
        if y_cand:
            match = re.search(r'\b(19\d\d|20\d\d)\b', str(y_cand))
            if match:
                published_year = int(match.group(1))
                break

    # Exact date resolution
    date_candidates = [
        next((p.get("date") for p in publication if p.get("date") and len(str(p.get("date"))) >= 10), None),
        next((d.get("date") for d in dissertation if d.get("date")), None),
        next((p.get("date") for p in provision if p.get("@type") == "OnlineAvailability" and p.get("date")), None),
        meta.get("creationDate")
    ]
    for d_cand in date_candidates:
        if d_cand and isinstance(d_cand, str) and len(d_cand) >= 10:
            try:
                published_date = datetime.strptime(d_cand[:10], "%Y-%m-%d")
                break
            except ValueError:
                pass

    # 7. Journal / Source Name (isPartOf Waterfall)
    journal_name = None
    is_part_of = record.get("isPartOf", [])
    if isinstance(is_part_of, dict): is_part_of = [is_part_of]

    root_series = record.get("hasSeries", [])
    if isinstance(root_series, dict): root_series = [root_series]

    def _get_title(obj):
        if not isinstance(obj, dict): return None
        t_array = obj.get("hasTitle", [])
        if isinstance(t_array, dict): t_array = [t_array]
        return t_array[0].get("mainTitle") if t_array else None

    # Step 1: Host Publication
    for p in is_part_of:
        journal_name = _get_title(p)
        if journal_name: break

    # Step 2: Nested Series
    if not journal_name:
        for p in is_part_of:
            if not isinstance(p, dict): continue
            h_series = p.get("hasSeries", [])
            if isinstance(h_series, dict): h_series = [h_series]
            for s in h_series:
                journal_name = _get_title(s)
                if journal_name: break
            if journal_name: break

    # Step 3: Root Series
    if not journal_name:
        for s in root_series:
            journal_name = _get_title(s)
            if journal_name: break

    # Step 4: Publisher Fallback
    if not journal_name:
        for p in publication:
            if not isinstance(p, dict): continue
            agent = p.get("agent", {})
            if isinstance(agent, dict):
                journal_name = agent.get("label") or agent.get("name")
                if journal_name: break

    # 8. Publication Type & Peer Review
    pub_type_base = "Unknown"
    is_peer_reviewed = False

    genre_forms = work.get("genreForm", [])
    if isinstance(genre_forms, dict):
        genre_forms = [genre_forms]

    for genre in genre_forms:
        if not isinstance(genre, dict): continue
        genre_uri = genre.get("@id", "")
        if "/output/" in genre_uri:
            pub_type_base = genre_uri.split("/output/")[-1]
        if genre_uri.endswith("/svep/ref"):
            is_peer_reviewed = True

    pub_type = f"{pub_type_base} [Peer Reviewed]" if is_peer_reviewed else pub_type_base

    # 9. Funding Info Extraction (Structured + Regex)
    funders = []

    # 9a. Structured Funder roles
    containers = [work] + is_part_of
    for c in containers:
        if not isinstance(c, dict): continue
        contribs = c.get("contribution", [])
        if isinstance(contribs, dict): contribs = [contribs]
        for contrib in contribs:
            if not isinstance(contrib, dict): continue
            roles = [r.get("@id", "") for r in contrib.get("role", []) if isinstance(r, dict)]
            if any(r.endswith("/relators/fnd") for r in roles):
                agent = contrib.get("agent", {})
                if isinstance(agent, dict):
                    name = agent.get("name") or agent.get("label")
                    if name and name not in funders:
                        funders.append(name)

    # 9b. Free-text Notes
    has_note = work.get("hasNote", [])
    if isinstance(has_note, dict): has_note = [has_note]
    funding_cues = ["funding information:", "funding agencies", "supported by", "grant agreement", "funded by",
                    "received funding"]

    for note in has_note:
        if not isinstance(note, dict) or note.get("@type") != "Note": continue
        label = note.get("label", "")
        label_low = label.lower()
        if any(cue in label_low for cue in funding_cues) and not label_low.endswith("posts"):
            if label not in funders:
                funders.append(label)

    funding_info = "; ".join(funders) if funders else None

    return {
        "swepub_id": swepub_id,
        "doi": doi,
        "title": title[:255] if title else "Unknown Title",
        "abstract": abstract,
        "publication_type": pub_type[:100] if pub_type else None,
        "journal_name": journal_name[:255] if journal_name else None,
        "published_year": published_year,
        "published_date": published_date,
        "authors_raw": authors_raw,
        "funding_info": funding_info,

        "is_duplicate": False,
        "is_relevant": None,
        "is_reviewed": False,
        "entities_matched": False,
        "wp_post_id": None,
        "has_processing_error": False,
        "processing_error_msg": None,
        "notes": None
    }


def _parse_xsearch(record: dict) -> dict:
    """Fallback defensive parser that cleans up legacy Xsearch strings."""
    swepub_id = None
    doi = None

    identifiers = record.get("identifier", [])
    if isinstance(identifiers, str):
        identifiers = [identifiers]

    for ident in identifiers:
        if not isinstance(ident, str):
            continue
        ident_lower = ident.lower()
        if "urn:nbn:se:" in ident_lower or "oai:" in ident_lower:
            if not swepub_id:
                swepub_id = ident
        if "10." in ident_lower:
            match = re.search(r'(10\.\d{4,9}/[-._;()/:A-Z0-9]+)', ident, re.IGNORECASE)
            if match:
                doi = match.group(1)

    title = record.get("title", "Unknown Title")
    if isinstance(title, list):
        title = title[0]

    abstract = record.get("description") or record.get("abstract") or record.get("summary")
    if isinstance(abstract, list):
        abstract = abstract[0]

    creators = record.get("creator", [])
    if isinstance(creators, str):
        creators = [creators]

    authors = []
    for c in creators:
        if isinstance(c, dict):
            c = c.get("name", "")
        c_str = str(c)
        c_str = re.sub(r'\b\d{4}-\d{0,4}\b', '', c_str)
        c_str = re.sub(r'\b(Professor|Docent|Associate Professor|PhD|Dr|Researcher)\b', '', c_str, flags=re.IGNORECASE)
        c_str = re.sub(r',\s*,', ',', c_str)
        c_str = re.sub(r'[,\s]+$', '', c_str).strip()
        c_str = re.sub(r'^[,]+', '', c_str).strip()
        if c_str:
            authors.append(c_str)

    authors_raw = "; ".join(authors) if authors else None

    pub_type = record.get("type", "Unknown")
    if isinstance(pub_type, list):
        pub_type = pub_type[0]

    journal_name = record.get("relation") or record.get("isPartOf") or record.get("publisher") or record.get("source")
    if isinstance(journal_name, list):
        journal_name = journal_name[0]

    pub_year_raw = record.get("date") or record.get("year") or record.get("issued") or record.get("publication")
    if isinstance(pub_year_raw, list):
        pub_year_raw = pub_year_raw[0]

    published_year = None
    if pub_year_raw:
        match = re.search(r'\b(19\d\d|20\d\d)\b', str(pub_year_raw))
        if match:
            published_year = int(match.group(1))

    return {
        "swepub_id": swepub_id,
        "doi": doi,
        "title": title[:255] if title else "Unknown Title",
        "abstract": str(abstract) if abstract else None,
        "publication_type": str(pub_type)[:100] if pub_type else None,
        "journal_name": str(journal_name)[:255] if journal_name else None,
        "published_year": published_year,
        "published_date": None,
        "authors_raw": authors_raw,
        "funding_info": None,

        "is_duplicate": False,
        "is_relevant": None,
        "is_reviewed": False,
        "entities_matched": False,
        "wp_post_id": None,
        "has_processing_error": False,
        "processing_error_msg": None,
        "notes": None
    }


def save_swepub_to_db(db: Session, raw_data: List[dict]) -> int:
    """Phase 2: Safely parses based on payload type and persists to DB."""
    items_saved = 0
    items_rejected_date = 0
    items_dropped_shield = 0
    items_duplicate = 0

    # Pre-calculate active names as (first, last) tuples for The Shield
    active_researchers = []
    for pr in crud.list_person_roles(db, active=True):
        if pr.person and pr.person.first_name and pr.person.last_name:
            first = pr.person.first_name.strip().lower()
            last = pr.person.last_name.strip().lower()
            active_researchers.append((first, last))

    for record in raw_data:
        if record.get("_format") == "bibframe":
            parsed_data = _parse_bibframe(record)
        else:
            parsed_data = _parse_xsearch(record)

        swepub_id = parsed_data.get("swepub_id")

        if not swepub_id:
            logger.warning("Skipping SwePub record without a valid swepub_id.")
            continue

        # THE FINAL REJECT: Date Floor Enforcement
        start_year_floor = record.get("_start_year", 2019)
        pub_year = parsed_data.get("published_year")
        if pub_year and pub_year < start_year_floor:
            # We silently drop it; it's older than our requested sync margin.
            items_rejected_date += 1
            continue

        # THE SHIELD: Chunk-based evaluation
        if record.get("_fetch_source") == "author":
            authors_raw = parsed_data.get("authors_raw") or ""
            author_chunks = [chunk.strip() for chunk in authors_raw.lower().split(";")]

            is_valid = False
            for first, last in active_researchers:
                # Check if BOTH the first and last name exist in the SAME chunk
                if any(first in chunk and last in chunk for chunk in author_chunks):
                    is_valid = True
                    break

            if not is_valid:
                logger.info(
                    f"Shield dropped {swepub_id}: Queried researcher not in authors (supervisor or false positive).")
                items_dropped_shield += 1
                continue

        # 1. Deduplication Check
        existing = crud.get_academic_by_swepub_id(db, swepub_id=swepub_id)
        if existing:
            items_duplicate += 1
            continue

        # 2. Incremental Committing via Try-Except
        try:
            pub_in = schemas.AcademicPublicationCreate(**parsed_data)
            crud.create_academic_publication(db, pub_in)
            items_saved += 1

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save SwePub record {swepub_id}: {e}")

    logger.info(
        f"Phase 3 Complete (DB Save): Processed {len(raw_data)} records | "
        f"Saved: {items_saved} | "
        f"Duplicates Skipped: {items_duplicate} | "
        f"Rejected (Older than floor): {items_rejected_date} | "
        f"Shield Drops (Not an author): {items_dropped_shield}"
    )

    return items_saved
