
"""Logic layer for the Wikipedia Article Extractor."""

from datetime import datetime
import re
from copy import copy
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag


# ============================================================
# Constants
# ============================================================

WIKIPEDIA_BASE_URL = "https://en.wikipedia.org/wiki/"

HEADERS = {
    "User-Agent": "ISOM3400WikipediaExtractor/1.0 (educational project)"
}

REQUEST_TIMEOUT = 10

EXCLUDED_SECTIONS = {
    "References",
    "External links",
    "See also",
    "Notes",
    "Further reading"
}

LICENCE = "CC BY-SA 4.0"

LICENCE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"


# ============================================================
# WikipediaExtractor Class
# ============================================================

class WikipediaExtractor:
    """Represents a Wikipedia article and its extracted sections."""

    def __init__(self, topic=None):
        self.error = None
        self.title = None
        self.url = ""
        self.soup = None
        self.sections = []

        if topic is not None:
            self.load_article(topic)

    def load_article(self, topic):
        self.error = None
        self.title = None
        self.url = ""
        self.soup = None
        self.sections = []

        article = self._fetch_article(topic)

        if article is None:
            return False

        self.title = article["title"]
        self.url = article["url"]
        self.soup = article["soup"]

        self.sections = self._list_sections(self.soup)

        return True

    def extract_selected(self, selected_numbers):
        self.error = None
        extracted_parts = []

        for number in selected_numbers:
            section = self.sections[number - 1]

            result = self._extract_section(section)

            if result:
                extracted_parts.append(result)

        return "\n\n".join(extracted_parts)

    def _fetch_article(self, topic):
        formatted_topic = topic.strip().replace(" ", "_")

        url = WIKIPEDIA_BASE_URL + quote(
            formatted_topic,
            safe="()"
        )

        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT
            )

            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            title_tag = soup.find("h1")

            if title_tag is None:
                self.error = "Error: Article title not found."
                return None

            return {
                "soup": soup,
                "title": title_tag.get_text(strip=True),
                "url": response.url,
            }

        except requests.exceptions.Timeout:
            self.error = (
                "Error: The request timed out. "
                "Please check your connection and try again."
            )

        except requests.exceptions.HTTPError as error:
            if error.response is not None:
                if error.response.status_code == 404:
                    self.error = "Error: Wikipedia article not found."
                else:
                    self.error = (
                        f"HTTP error: {error.response.status_code}"
                    )
            else:
                self.error = f"HTTP error: {error}"

        except requests.exceptions.RequestException as error:
            self.error = f"Network error: {error}"

        except (AttributeError, TypeError, ValueError) as error:
            self.error = f"Error while parsing the article: {error}"

        return None

    def _list_sections(self, soup):
        content = soup.find("div", id="mw-content-text")

        if content is None:
            self.error = "Error: Article content not found."
            return []

        headings = content.find_all("h2")

        sections = []

        for heading in headings:
            title = heading.get_text(" ", strip=True)
            title = title.replace("[edit]", "").strip()

            if not title or title in EXCLUDED_SECTIONS:
                continue

            sections.append({
                "title": title,
                "heading": heading
            })

        if not sections:
            self.error = "No article sections found."

        return sections

    def _extract_section(self, section):
        title = section["title"]
        heading = section["heading"]

        extracted = [f"\n{'=' * 50}", title, "=" * 50]

        next_heading = heading.find_next("h2")

        content = heading.find_parent(
            "div", id="mw-content-text"
        )

        if content is None:
            self.error = "Error: Could not locate article content."
            return ""

        for element in heading.next_elements:

            if element is next_heading:
                break

            if not isinstance(element, Tag):
                continue

            if content not in element.parents:
                continue

            # Skip nested elements handled by their parents
            if element.name in ["p", "ul", "ol", "table"]:
                if element.find_parent(["p", "ul", "ol", "table"]):
                    continue

            if element.name == "p":
                text = _clean_text(element)

                if text:
                    extracted.append(text + "\n")

            elif element.name in ["h3", "h4"]:
                text = _clean_text(element)

                if text:
                    extracted.append(f"\n--- {text} ---")

            elif element.name in ["ul", "ol"]:
                extracted.extend(_format_list(element))
                extracted.append("")

            elif element.name == "table":
                for row in element.find_all("tr"):
                    cells = row.find_all(
                        ["th", "td"], recursive=False
                    )

                    values = [
                        _clean_text(cell) for cell in cells
                    ]

                    if values:
                        extracted.append(" | ".join(values))

                extracted.append("")

        return "\n".join(extracted)


# ============================================================
# Pure Helper Functions
# ============================================================

def _clean_text(element):
    # Preserve the original HTML
    element_copy = copy(element)

    # Remove citation references
    for reference in element_copy.find_all(
        "sup", class_="reference"
    ):
        reference.decompose()

    text = element_copy.get_text(" ", strip=True)

    # Remove remaining numeric citation markers
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\[citation needed\]", "", text, flags=re.I)

    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def _format_list(list_element, level=0):
    lines = []

    for index, item in enumerate(
        list_element.find_all("li", recursive=False),
        start=1
    ):
        item_copy = copy(item)

        for nested in item_copy.find_all(["ul", "ol"]):
            nested.decompose()

        text = _clean_text(item_copy)

        indent = "  " * level

        if list_element.name == "ol":
            marker = f"{index}."
        else:
            marker = "-"

        if text:
            lines.append(f"{indent}{marker} {text}")

        # Recursively format nested lists
        for nested in item.find_all(
            ["ul", "ol"], recursive=False
        ):
            lines.extend(_format_list(nested, level + 1))

    return lines


def safe_filename(article_title):
    safe_title = re.sub(r'[^\w\s-]', '', article_title).strip()
    safe_title = re.sub(r'\s+', '_', safe_title)
    return safe_title or "Wikipedia_Article"


def numbered_filename(filename, downloaded_filenames):
    stem, dot, extension = filename.rpartition(".")
    if not dot:
        stem, extension = filename, ""
    suffix = f".{extension}" if dot else ""
    candidate = filename
    counter = 2
    while candidate in downloaded_filenames:
        candidate = f"{stem} ({counter}){suffix}"
        counter += 1
    return candidate


def format_txt(article_title, article_url, sections):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = (
        f"WIKIPEDIA ARTICLE EXTRACTOR\n"
        f"{'=' * 60}\n"
        f"Article Title: {article_title}\n"
        f"Source URL: {article_url}\n"
        f"Extraction Time: {timestamp}\n"
        f"Licence: {LICENCE}\n"
        f"Licence URL: {LICENCE_URL}\n"
        f"{'=' * 60}\n\n"
    )
    return header + "\n\n".join(section["content"] for section in sections)
