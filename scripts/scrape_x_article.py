#!/usr/bin/env python3
"""Scrape X articles using the openclaw browser, preserving formatting as Typst markup."""

import json
import re
import sys
import urllib.request

# JS to extract article content from X's DraftJS-based article renderer
EXTRACT_JS = r"""() => {
  const root = document.querySelector('.DraftEditor-root');
  if (!root) return { error: 'no DraftEditor-root found' };

  const blocks = root.querySelectorAll('[data-block="true"]');
  const result = [];

  for (const block of blocks) {
    // Determine block type from class
    const cls = block.className || '';
    let type = 'paragraph';
    if (cls.includes('longform-header-one')) type = 'h1';
    else if (cls.includes('longform-header-two')) type = 'h2';
    else if (cls.includes('longform-header-three')) type = 'h3';
    else if (cls.includes('longform-blockquote')) type = 'blockquote';
    else if (cls.includes('longform-unordered-list-item')) type = 'ul';
    else if (cls.includes('longform-ordered-list-item')) type = 'ol';

    // Extract inline formatting
    const inner = block.querySelector('.public-DraftStyleDefault-block') || block;
    const spans = inner.childNodes;
    const parts = [];

    function extractNode(node) {
      if (node.nodeType === 3) { // text node
        return node.textContent;
      }
      if (node.nodeType !== 1) return '';

      const style = node.style || {};
      const tag = node.tagName;
      let text = '';
      for (const child of node.childNodes) {
        text += extractNode(child);
      }

      // Check for bold/italic via computed style or style attribute
      const cs = window.getComputedStyle(node);
      const isBold = cs.fontWeight === 'bold' || parseInt(cs.fontWeight) >= 700;
      const isItalic = cs.fontStyle === 'italic';

      // Only wrap leaf-level text spans, not containers
      if (text && node.closest('[data-text="true"]') === node || node.getAttribute('data-text') === 'true') {
        if (isBold && isItalic) return '*_' + text + '_*';
        if (isBold) return '*' + text + '*';
        if (isItalic) return '_' + text + '_';
      }
      return text;
    }

    let fullText = '';
    for (const child of inner.childNodes) {
      fullText += extractNode(child);
    }

    if (fullText || type !== 'paragraph') {
      result.push({ type, text: fullText });
    }
  }

  // Get article title from the page header
  let title = '';
  const titleEl = document.querySelector('h1[data-testid="article-title"]')
    || document.querySelector('div[data-testid="article-cover-container"]')?.closest('article')?.querySelector('h1');
  if (titleEl) title = titleEl.textContent;

  return { blocks: result, title };
}"""


def blocks_to_typst(blocks):
    """Convert extracted blocks to Typst markup."""
    lines = []
    prev_type = None

    for block in blocks:
        btype = block['type']
        text = block['text'].strip()
        if not text and btype == 'paragraph':
            lines.append('')
            continue

        # Escape Typst-dangerous chars in text, but preserve * and _ (formatting)
        # We do minimal escaping since the JS already outputs Typst formatting
        text = _escape_typst_body(text)

        if btype == 'h1':
            if prev_type and prev_type != 'h1':
                lines.append('')
            lines.append(f'== {text}')
            lines.append('')
        elif btype == 'h2':
            lines.append(f'=== {text}')
            lines.append('')
        elif btype == 'h3':
            lines.append(f'==== {text}')
            lines.append('')
        elif btype == 'blockquote':
            lines.append(f'#quote[{text}]')
            lines.append('')
        elif btype == 'ul':
            lines.append(f'- {text}')
        elif btype == 'ol':
            lines.append(f'+ {text}')
        else:
            lines.append(text)
            lines.append('')

        prev_type = btype

    # Clean up multiple blank lines
    result = '\n'.join(lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()


def _escape_typst_body(text):
    """Escape dangerous Typst chars but preserve * and _ formatting markers."""
    # We need to be careful: escape \, #, `, <, >, @, $, ~
    # But NOT * and _ (those are our formatting)
    text = text.replace('\\', '\\\\')
    text = text.replace('#', '\\#')
    text = text.replace('`', '\\`')
    text = text.replace('<', '\\<')
    text = text.replace('>', '\\>')
    text = text.replace('@', '\\@')
    text = text.replace('$', '\\$')
    text = text.replace('~', '\\~')
    return text


def get_metadata_from_fxtwitter(user, status_id):
    """Get article title and author from fxtwitter API."""
    url = f"https://api.fxtwitter.com/{user}/status/{status_id}"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        tweet = data.get('tweet', {})
        author = tweet.get('author', {}).get('name', user)
        article = tweet.get('article', {})
        title = article.get('title', '') or tweet.get('text', '')[:80]
        return {'title': title.strip(), 'author': author}
    except Exception as e:
        print(f"Warning: fxtwitter API failed: {e}", file=sys.stderr)
        return {'title': '', 'author': user}


def parse_x_url(url):
    """Extract username and status ID from X URL."""
    m = re.search(r'(?:twitter\.com|x\.com)/(\w+)/status/(\d+)', url)
    if not m:
        return None, None
    return m.group(1), m.group(2)


def scrape_x_article(url, browser_fn=None):
    """
    Scrape an X article. Returns {"title": ..., "author": ..., "body": ...}
    where body is Typst-formatted.
    
    browser_fn: async function that takes (url, js_code) and returns the evaluation result.
                If None, returns the JS code for manual execution.
    """
    user, status_id = parse_x_url(url)
    if not user:
        return None

    # Get metadata
    meta = get_metadata_from_fxtwitter(user, status_id)

    if browser_fn:
        # Navigate and extract
        result = browser_fn(url, EXTRACT_JS)
        if result and 'blocks' in result:
            body = blocks_to_typst(result['blocks'])
            title = result.get('title') or meta['title']
            return {
                'title': title,
                'author': meta['author'],
                'body': body
            }

    # Return metadata with JS for manual browser execution
    return {
        'title': meta['title'],
        'author': meta['author'],
        'body': '',
        '_js': EXTRACT_JS,
        '_url': url
    }


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: scrape_x_article.py <url>", file=sys.stderr)
        sys.exit(1)
    url = sys.argv[1]
    result = scrape_x_article(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
