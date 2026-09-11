from __future__ import annotations

import ipaddress
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from email.message import Message
from html import unescape
from html.parser import HTMLParser
from typing import Callable

from services.news_errors import NewsInvalidSource, NewsSourceBlocked, NewsSourceFetchError, NewsSourceParseError, NewsSourceSecurityError


@dataclass(frozen=True, slots=True)
class ExtractedSource:
    url: str
    title: str
    author: str
    published_at: str | None
    publisher: str
    content_text: str
    content_type: str
    charset: str


class SourceExtractor:
    def extract(self, content: bytes, *, content_type: str, charset: str, url: str) -> ExtractedSource:
        raise NotImplementedError


class PlainTextExtractor(SourceExtractor):
    def extract(self, content: bytes, *, content_type: str, charset: str, url: str) -> ExtractedSource:
        try:
            text = content.decode(charset or "utf-8", errors="strict")
        except (LookupError, UnicodeDecodeError):
            text = content.decode("utf-8", errors="replace")
        return ExtractedSource(url, "", "", None, urllib.parse.urlsplit(url).hostname or "", text.strip(), content_type, charset or "utf-8")


class _ArticleHTMLParser(HTMLParser):
    BLOCKED = {"script", "style", "noscript", "nav", "footer", "header", "aside", "form", "svg"}
    TEXT_TAGS = {"p", "h1", "h2", "h3", "h4", "li", "blockquote", "figcaption"}
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""; self.author = ""; self.published = None; self.site_name = ""
        self._tag_stack: list[str] = []; self._blocked = 0; self._article_depth = 0; self._title_depth = 0
        self._buf: list[str] = []; self.article_chunks: list[str] = []; self.body_chunks: list[str] = []
    def handle_starttag(self, tag: str, attrs) -> None:
        tag=tag.lower(); attrs=dict(attrs); self._tag_stack.append(tag)
        if tag in self.BLOCKED: self._blocked += 1
        if tag in {"article","main"}: self._article_depth += 1
        if tag == "title": self._title_depth += 1
        if tag == "meta":
            key=(attrs.get("property") or attrs.get("name") or "").lower(); value=(attrs.get("content") or "").strip()
            if key in {"og:title","twitter:title"} and value: self.title=value
            elif key in {"author","article:author","byl"} and value: self.author=value
            elif key in {"article:published_time","date","datepublished","publishdate"} and value: self.published=value
            elif key=="og:site_name" and value: self.site_name=value
        if tag in self.TEXT_TAGS: self._flush()
    def handle_endtag(self, tag: str) -> None:
        tag=tag.lower()
        if tag in self.TEXT_TAGS: self._flush()
        if tag == "title": self._title_depth=max(0,self._title_depth-1)
        if tag in {"article","main"}: self._article_depth=max(0,self._article_depth-1)
        if tag in self.BLOCKED: self._blocked=max(0,self._blocked-1)
        if self._tag_stack: self._tag_stack.pop()
    def handle_data(self, data: str) -> None:
        if self._blocked: return
        text=" ".join(data.split())
        if not text: return
        if self._title_depth and not self.title: self.title=(self.title+" "+text).strip()
        self._buf.append(text)
    def _flush(self) -> None:
        if not self._buf: return
        text=unescape(" ".join(self._buf)).strip(); self._buf=[]
        if len(text)<2: return
        self.body_chunks.append(text)
        if self._article_depth: self.article_chunks.append(text)
    def close(self) -> None:
        self._flush(); super().close()


class HtmlArticleExtractor(SourceExtractor):
    def extract(self, content: bytes, *, content_type: str, charset: str, url: str) -> ExtractedSource:
        try: html=content.decode(charset or "utf-8", errors="replace")
        except LookupError: html=content.decode("utf-8",errors="replace")
        parser=_ArticleHTMLParser()
        try: parser.feed(html); parser.close()
        except Exception as exc: raise NewsSourceParseError("The HTML source could not be parsed.") from exc
        chunks=parser.article_chunks or parser.body_chunks
        # Keep useful article text and avoid UI clutter dominating the result.
        chunks=[x for x in chunks if len(x)>=20 or x==parser.title]
        text="\n\n".join(dict.fromkeys(chunks)).strip()
        if not text: raise NewsSourceParseError("No readable article text was found.")
        host=urllib.parse.urlsplit(url).hostname or ""
        return ExtractedSource(url,parser.title.strip(),parser.author.strip(),parser.published,parser.site_name.strip() or host,text,content_type,charset or "utf-8")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class PublicURLPolicy:
    def __init__(self, resolver: Callable[..., list[tuple]] | None=None) -> None:
        self.resolver=resolver or socket.getaddrinfo
    def validate(self,url:str)->urllib.parse.SplitResult:
        try: parsed=urllib.parse.urlsplit((url or "").strip())
        except ValueError as exc: raise NewsInvalidSource("Enter a valid URL.") from exc
        if parsed.scheme.lower() not in {"http","https"}: raise NewsSourceSecurityError()
        if not parsed.hostname: raise NewsInvalidSource("Enter a URL with a valid host.")
        host=parsed.hostname.strip(".").lower()
        if host in {"localhost","localhost.localdomain"} or host.endswith(".localhost") or host.endswith(".local"):
            raise NewsSourceSecurityError()
        if parsed.username or parsed.password: raise NewsSourceSecurityError("URLs with embedded credentials are not allowed.")
        port=parsed.port or (443 if parsed.scheme.lower()=="https" else 80)
        try: infos=self.resolver(host,port,type=socket.SOCK_STREAM)
        except OSError as exc: raise NewsSourceFetchError("The source host could not be resolved.") from exc
        if not infos: raise NewsSourceFetchError("The source host could not be resolved.")
        for info in infos:
            try: ip=ipaddress.ip_address(info[4][0])
            except ValueError: raise NewsSourceSecurityError()
            if not ip.is_global:
                raise NewsSourceSecurityError()
        return parsed


class NewsSourceFetchService:
    USER_AGENT="MMOVideoStudio/0.1 NewsSourceFetcher (+local desktop application)"
    REDIRECT_CODES={301,302,303,307,308}
    def __init__(self, *, policy:PublicURLPolicy|None=None, max_bytes:int=5*1024*1024, timeout:float=10.0, max_redirects:int=5, opener=None) -> None:
        self.policy=policy or PublicURLPolicy(); self.max_bytes=max(1024,int(max_bytes)); self.timeout=float(timeout); self.max_redirects=max(0,int(max_redirects)); self.opener=opener or urllib.request.build_opener(_NoRedirect())
        self.html=HtmlArticleExtractor(); self.plain=PlainTextExtractor()
    def validate_url(self,url:str)->bool:
        self.policy.validate(url); return True
    def fetch(self,url:str)->ExtractedSource:
        current=(url or "").strip()
        for redirect_count in range(self.max_redirects+1):
            self.policy.validate(current)
            req=urllib.request.Request(current,headers={"User-Agent":self.USER_AGENT,"Accept":"text/html,text/plain;q=0.9"})
            try:
                response=self.opener.open(req,timeout=self.timeout)
                return self._read_response(response,current)
            except urllib.error.HTTPError as exc:
                if exc.code in self.REDIRECT_CODES:
                    if redirect_count>=self.max_redirects: raise NewsSourceFetchError("Too many source redirects.") from exc
                    location=exc.headers.get("Location")
                    if not location: raise NewsSourceFetchError("Source redirect did not include a destination.") from exc
                    current=urllib.parse.urljoin(current,location)
                    self.policy.validate(current)
                    continue
                if exc.code==429: raise NewsSourceFetchError("Source temporarily limited requests.") from exc
                if exc.code in {401,403}: raise NewsSourceBlocked("This page did not provide accessible article text.") from exc
                if exc.code in {404,410}: raise NewsSourceFetchError("The source page is not available.") from exc
                if 500<=exc.code<=599: raise NewsSourceFetchError("The source server is temporarily unavailable.") from exc
                raise NewsSourceFetchError(f"The source returned HTTP {exc.code}.") from exc
            except (TimeoutError, socket.timeout) as exc: raise NewsSourceFetchError("The source request timed out.") from exc
            except urllib.error.URLError as exc: raise NewsSourceFetchError("The source could not be reached.") from exc
        raise NewsSourceFetchError("The source could not be fetched.")
    def _read_response(self,response,url:str)->ExtractedSource:
        headers:Message=response.headers
        content_type=(headers.get_content_type() or "").lower()
        if content_type not in {"text/html","application/xhtml+xml","text/plain"}:
            raise NewsSourceBlocked("Only public HTML or plain-text sources are supported.")
        length=headers.get("Content-Length")
        if length:
            try:
                if int(length)>self.max_bytes: raise NewsSourceBlocked("Source content is larger than the allowed limit.")
            except ValueError: pass
        raw=response.read(self.max_bytes+1)
        if len(raw)>self.max_bytes: raise NewsSourceBlocked("Source content is larger than the allowed limit.")
        charset=headers.get_content_charset() or "utf-8"
        extractor=self.html if content_type in {"text/html","application/xhtml+xml"} else self.plain
        return extractor.extract(raw,content_type=content_type,charset=charset,url=response.geturl() if hasattr(response,"geturl") else url)
