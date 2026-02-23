#!/usr/bin/env python3
"""Fetch article content from various sources. Returns JSON."""

import json
import re
import sys
import urllib.request
import urllib.error
from html.parser import HTMLParser
from urllib.parse import urlparse


class TextExtractor(HTMLParser):
    """Simple HTML→text extractor that preserves paragraphs and headings."""
    def __init__(self):
        super().__init__()
        self.result = []
        self.current = []
        self.skip = False
        self.skip_tags = {'script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript'}
        self.block_tags = {'p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'blockquote', 'br', 'tr'}
        self.heading_tags = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
        self.in_heading = None
        self.title = None
        self.in_title = False
        self.title_buf = []
        self.in_article = False
        self.article_buf = []
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.skip_tags:
            self.skip = True
            self.depth += 1
            return
        if tag == 'title':
            self.in_title = True
        if tag == 'article':
            self.in_article = True
        if tag in self.heading_tags:
            self.in_heading = tag
        if tag in self.block_tags:
            self._flush()

    def handle_endtag(self, tag):
        if tag in self.skip_tags:
            self.depth -= 1
            if self.depth <= 0:
                self.skip = False
                self.depth = 0
            return
        if tag == 'title':
            self.in_title = False
            self.title = ''.join(self.title_buf).strip()
        if tag in self.heading_tags:
            text = ''.join(self.current).strip()
            if text:
                level = int(tag[1])
                prefix = '=' * level + ' '
                self.result.append(prefix + text)
            self.current = []
            self.in_heading = None
            return
        if tag in self.block_tags:
            self._flush()

    def handle_data(self, data):
        if self.in_title:
            self.title_buf.append(data)
        if self.skip:
            return
        self.current.append(data)

    def _flush(self):
        text = ''.join(self.current).strip()
        if text:
            self.result.append(text)
        self.current = []

    def get_text(self):
        self._flush()
        return '\n\n'.join(self.result)


def fetch_url(url, as_json=False):
    """Fetch a URL, return text or parsed JSON."""
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read().decode('utf-8', errors='replace')
            return json.loads(data) if as_json else data
    except Exception as e:
        print(f"Warning: Failed to fetch {url}: {e}", file=sys.stderr)
        return None


def extract_from_html(html):
    """Extract title and body text from HTML."""
    ext = TextExtractor()
    ext.feed(html)
    return ext.title or "", ext.get_text()


def fetch_x_post(url):
    """Fetch an X/Twitter post or article."""
    m = re.search(r'(?:twitter\.com|x\.com)/(\w+)/status/(\d+)', url)
    if not m:
        return None
    user, status_id = m.group(1), m.group(2)

    # Try fxtwitter API
    api_url = f"https://api.fxtwitter.com/{user}/status/{status_id}"
    data = fetch_url(api_url, as_json=True)
    if not data or 'tweet' not in data:
        return None

    tweet = data['tweet']

    # Check if it's an X article
    if tweet.get('article'):
        article = tweet['article']
        title = article.get('title', tweet.get('text', '')[:80])
        # Try to get full content from xcancel
        xcancel_url = f"https://xcancel.com/{user}/status/{status_id}"
        html = fetch_url(xcancel_url)
        body = ""
        if html:
            _, body = extract_from_html(html)
        if not body:
            body = article.get('preview_text', tweet.get('text', ''))
        return {
            'title': title,
            'author': tweet.get('author', {}).get('name', user),
            'body': body
        }

    # Regular tweet
    return {
        'title': f"Post by @{user}",
        'author': tweet.get('author', {}).get('name', user),
        'body': tweet.get('text', '')
    }


def fetch_medium(url):
    """Fetch a Medium article."""
    html = fetch_url(url)
    if not html:
        return None
    title, body = extract_from_html(html)
    # Try to get author from meta
    author = ""
    m = re.search(r'<meta[^>]+name="author"[^>]+content="([^"]+)"', html)
    if m:
        author = m.group(1)
    return {'title': title or "Medium Article", 'author': author, 'body': body}


def fetch_wechat(url):
    """Fetch a WeChat article."""
    html = fetch_url(url)
    if not html:
        return None
    title, body = extract_from_html(html)
    author = ""
    m = re.search(r'var nickname\s*=\s*"([^"]+)"', html)
    if m:
        author = m.group(1)
    return {'title': title or "WeChat Article", 'author': author, 'body': body}


def fetch_generic(url):
    """Fetch any web article."""
    html = fetch_url(url)
    if not html:
        return None
    title, body = extract_from_html(html)
    author = ""
    m = re.search(r'<meta[^>]+name="author"[^>]+content="([^"]+)"', html)
    if m:
        author = m.group(1)
    return {'title': title or url, 'author': author, 'body': body}


def fetch_article(url):
    """Route URL to appropriate fetcher."""
    parsed = urlparse(url)
    host = parsed.hostname or ""

    if 'twitter.com' in host or 'x.com' in host:
        return fetch_x_post(url)
    elif 'medium.com' in host or host.endswith('.medium.com'):
        return fetch_medium(url)
    elif 'mp.weixin.qq.com' in host:
        return fetch_wechat(url)
    else:
        return fetch_generic(url)


if __name__ == '__main__':
    urls = sys.argv[1:]
    if not urls:
        urls = [line.strip() for line in sys.stdin if line.strip()]
    results = []
    for u in urls:
        r = fetch_article(u)
        if r:
            results.append(r)
        else:
            print(f"Warning: Could not fetch {u}", file=sys.stderr)
    print(json.dumps(results, ensure_ascii=False, indent=2))
