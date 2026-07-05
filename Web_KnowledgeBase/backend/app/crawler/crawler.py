"""Async breadth-first crawler bounded by depth, page count and domain."""
from __future__ import annotations

import asyncio
import urllib.robotparser
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional
from urllib.parse import urldefrag, urlparse

import httpx

from .extractor import extract


@dataclass
class CrawledPage:
    url: str
    title: str
    text: str
    depth: int
    parent_url: Optional[str]
    headings: list[str] = field(default_factory=list)


def _normalize(url: str) -> str:
    url, _ = urldefrag(url)
    return url.rstrip("/") or url


def _same_domain(a: str, b: str) -> bool:
    na, nb = urlparse(a).netloc.lower(), urlparse(b).netloc.lower()
    na = na[4:] if na.startswith("www.") else na
    nb = nb[4:] if nb.startswith("www.") else nb
    return na == nb


class Crawler:
    def __init__(
        self,
        *,
        max_depth: int,
        max_pages: int,
        concurrency: int,
        timeout: float,
        user_agent: str,
        same_domain_only: bool,
        respect_robots: bool,
    ) -> None:
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.concurrency = concurrency
        self.timeout = timeout
        self.user_agent = user_agent
        self.same_domain_only = same_domain_only
        self.respect_robots = respect_robots
        self._robots: dict[str, Optional[urllib.robotparser.RobotFileParser]] = {}

    async def _load_robots(self, client: httpx.AsyncClient, seed: str) -> None:
        if not self.respect_robots:
            return
        parsed = urlparse(seed)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if base in self._robots:
            return
        rp = urllib.robotparser.RobotFileParser()
        try:
            resp = await client.get(f"{base}/robots.txt")
            if resp.status_code == 200:
                rp.parse(resp.text.splitlines())
                self._robots[base] = rp
            else:
                self._robots[base] = None
        except httpx.HTTPError:
            self._robots[base] = None

    def _allowed(self, url: str) -> bool:
        if not self.respect_robots:
            return True
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        rp = self._robots.get(base)
        if rp is None:
            return True
        return rp.can_fetch(self.user_agent, url)

    async def crawl(
        self,
        seed_url: str,
        on_page: Optional[Callable[[CrawledPage], Awaitable[None]]] = None,
    ) -> list[CrawledPage]:
        seed = _normalize(seed_url)
        seen: set[str] = {seed}
        results: list[CrawledPage] = []
        # Frontier holds one BFS level at a time: list of (url, parent, depth).
        frontier: list[tuple[str, Optional[str], int]] = [(seed, None, 0)]
        sem = asyncio.Semaphore(self.concurrency)

        headers = {"User-Agent": self.user_agent, "Accept": "text/html,application/xhtml+xml"}
        async with httpx.AsyncClient(
            headers=headers,
            timeout=self.timeout,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=self.concurrency * 2),
        ) as client:
            await self._load_robots(client, seed)

            while frontier and len(results) < self.max_pages:
                async def fetch(item: tuple[str, Optional[str], int]):
                    url, parent, depth = item
                    if not self._allowed(url):
                        return None
                    async with sem:
                        try:
                            resp = await client.get(url)
                        except httpx.HTTPError:
                            return None
                    ctype = resp.headers.get("content-type", "")
                    if resp.status_code != 200 or "html" not in ctype.lower():
                        return None
                    ex = extract(resp.text, str(resp.url))
                    page = CrawledPage(
                        url=_normalize(str(resp.url)),
                        title=ex.title,
                        text=ex.text,
                        depth=depth,
                        parent_url=parent,
                        headings=ex.headings,
                    )
                    return page, ex.links

                batch = await asyncio.gather(*(fetch(item) for item in frontier))

                next_frontier: list[tuple[str, Optional[str], int]] = []
                for item, fetched in zip(frontier, batch):
                    if fetched is None:
                        continue
                    page, links = fetched
                    if not page.text.strip():
                        continue
                    results.append(page)
                    if on_page:
                        await on_page(page)
                    if len(results) >= self.max_pages:
                        break
                    if page.depth >= self.max_depth:
                        continue
                    for link in links:
                        nlink = _normalize(link)
                        if nlink in seen:
                            continue
                        if self.same_domain_only and not _same_domain(seed, nlink):
                            continue
                        seen.add(nlink)
                        next_frontier.append((nlink, page.url, page.depth + 1))
                frontier = next_frontier

        return results[: self.max_pages]
