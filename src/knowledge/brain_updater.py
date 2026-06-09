"""Knowledge brain updater for SECOND-KNOWLEDGE-BRAIN.md auto-update."""
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
import re
import logging

logger = logging.getLogger(__name__)


class KnowledgeBrainUpdater:
    """Auto-update SECOND-KNOWLEDGE-BRAIN.md with new research papers."""

    SOURCES = {
        'arxiv_cs_ir': 'https://arxiv.org/list/cs.IR/recent',
        'arxiv_cs_ai': 'https://arxiv.org/list/cs.AI/recent',
        'arxiv_cs_cl': 'https://arxiv.org/list/cs.CL/recent',
        'huggingface_papers': 'https://huggingface.co/papers',
    }

    def __init__(self, markdown_path: Optional[str] = None):
        """Initialize knowledge brain updater.

        Args:
            markdown_path: Path to SECOND-KNOWLEDGE-BRAIN.md
        """
        from pathlib import Path

        self.markdown_path = markdown_path or (Path(__file__).parent.parent.parent / "SECOND-KNOWLEDGE-BRAIN.md")
        self.browser_config = BrowserConfig(headless=True, verbose=False)
        self.crawler_config = CrawlerRunConfig(bypass_cache=True)

    async def update_knowledge_brain(self) -> bool:
        """Fetch new papers and append to SECOND-KNOWLEDGE-BRAIN.md.

        Returns:
            True if update successful
        """
        logger.info("Starting knowledge brain update")

        new_entries = []

        # Fetch from ArXiv
        arxiv_entries = await self._fetch_arxiv_papers()
        new_entries.extend(arxiv_entries)

        # Fetch from HuggingFace
        hf_entries = await self._fetch_huggingface_papers()
        new_entries.extend(hf_entries)

        if not new_entries:
            logger.info("No new entries found")
            return True

        # Append to markdown file
        return await self._append_to_markdown(new_entries)

    async def _fetch_arxiv_papers(self) -> List[Dict[str, Any]]:
        """Fetch papers from ArXiv."""
        entries = []

        for source_name, url in self.SOURCES.items():
            if not source_name.startswith('arxiv'):
                continue

            try:
                async with AsyncWebCrawler(config=self.browser_config) as crawler:
                    result = await crawler.arun(url=url, config=self.crawler_config)

                    if not result.success:
                        logger.warning(f"Failed to fetch {source_name}")
                        continue

                    papers = self._parse_arxiv_html(result.html, source_name)
                    entries.extend(papers)

            except Exception as e:
                logger.error(f"Error fetching {source_name}: {e}")

        return entries

    async def _fetch_huggingface_papers(self) -> List[Dict[str, Any]]:
        """Fetch papers from HuggingFace."""
        entries = []

        try:
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                result = await crawler.arun(
                    url=self.SOURCES['huggingface_papers'],
                    config=self.crawler_config
                )

                if result.success:
                    papers = self._parse_huggingface_html(result.html)
                    entries.extend(papers)

        except Exception as e:
            logger.error(f"Error fetching HuggingFace papers: {e}")

        return entries

    def _parse_arxiv_html(self, html: str, source: str) -> List[Dict[str, Any]]:
        """Parse ArXiv listing page."""
        from bs4 import BeautifulSoup

        entries = []
        soup = BeautifulSoup(html, 'html.parser')

        # ArXiv listings are in <dl> elements
        listings = soup.select('dl dt') + soup.select('div.list-dat')

        for item in listings[:10]:  # Limit to 10 most recent
            try:
                title_elem = item.find_next('dt') if item.name == 'dd' else item
                if not title_elem:
                    continue

                title_link = title_elem.find('a')
                if not title_link:
                    continue

                title = title_link.get_text(strip=True)
                arxiv_url = title_link.get('href', '')

                if arxiv_url and not arxiv_url.startswith('http'):
                    arxiv_url = 'https://arxiv.org' + arxiv_url

                # Extract ID from URL
                arxiv_id = arxiv_url.split('/')[-1] if arxiv_url else ''

                # Get authors and abstract
                abstract_elem = item.find_next('dd') if item.name == 'dt' else item
                abstract = ''
                authors = []

                if abstract_elem:
                    abstract_p = abstract_elem.find('p', class_='abstract')
                    if abstract_p:
                        abstract = abstract_p.get_text(strip=True)

                    author_divs = abstract_elem.select('div.list-authors')
                    if author_divs:
                        authors = [a.get_text(strip=True) for a in author_divs]

                entries.append({
                    'type': 'paper',
                    'title': title,
                    'source': 'ArXiv',
                    'url': arxiv_url,
                    'arxiv_id': arxiv_id,
                    'authors': authors,
                    'abstract': abstract[:500] if abstract else '',
                    'date': datetime.now().strftime('%Y-%m-%d')
                })

            except Exception as e:
                logger.debug(f"Error parsing ArXiv item: {e}")
                continue

        return entries

    def _parse_huggingface_html(self, html: str) -> List[Dict[str, Any]]:
        """Parse HuggingFace papers page."""
        from bs4 import BeautifulSoup

        entries = []
        soup = BeautifulSoup(html, 'html.parser')

        # Look for paper cards
        paper_cards = soup.select('a[href*="/papers/"]')

        for card in paper_cards[:5]:
            try:
                title = card.get_text(strip=True)
                url = 'https://huggingface.co' + card.get('href', '')

                entries.append({
                    'type': 'paper',
                    'title': title,
                    'source': 'HuggingFace',
                    'url': url,
                    'date': datetime.now().strftime('%Y-%m-%d')
                })

            except Exception as e:
                logger.debug(f"Error parsing HF paper: {e}")
                continue

        return entries

    async def _append_to_markdown(self, entries: List[Dict[str, Any]]) -> bool:
        """Append new entries to SECOND-KNOWLEDGE-BRAIN.md."""
        try:
            # Read existing file
            if self.markdown_path.exists():
                content = self.markdown_path.read_text(encoding='utf-8')
            else:
                content = "# SECOND-KNOWLEDGE-BRAIN.md\n\n"

            # Find Knowledge Update Log section
            log_section_start = content.find('## Knowledge Update Log')

            if log_section_start == -1:
                # Create new section
                content += "\n\n## Knowledge Update Log\n\n"
                log_section_start = len(content)

            # Prepare new entries
            today = date.today()
            new_log_content = "\n### Auto-Update Entries\n\n"

            for entry in entries:
                if entry['type'] == 'paper':
                    new_log_content += f"#### [{entry['date']}] {entry['title']}\n"
                    new_log_content += f"- **Source**: {entry['source']}\n"
                    new_log_content += f"- **Link**: {entry['url']}\n"
                    if entry.get('abstract'):
                        new_log_content += f"- **Abstract**: {entry['abstract'][:200]}...\n"
                    new_log_content += "\n"

            # Insert before the log table
            table_start = content.find('| Date |', log_section_start)
            if table_start == -1:
                # Append at end of section
                insert_pos = len(content)
            else:
                insert_pos = table_start

            updated_content = content[:insert_pos] + new_log_content + content[insert_pos:]

            # Write back
            self.markdown_path.write_text(updated_content, encoding='utf-8')
            logger.info(f"Updated {self.markdown_path.name} with {len(entries)} new entries")

            return True

        except Exception as e:
            logger.error(f"Failed to update markdown: {e}")
            return False
