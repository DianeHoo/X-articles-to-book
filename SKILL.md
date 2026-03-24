# articles-to-book

Convert web articles and X Articles into beautifully formatted PDF books with preserved formatting (bold, italic, headings, block quotes, lists).

## How It Works

### Step 1: Scrape X Articles (via openclaw browser)

X Articles (long-form posts) cannot be scraped via API or web_fetch. The only working method is using the openclaw browser tool to run JS on the loaded page.

**Scraping JS:** Extracts from `DraftEditor-root` > `[data-block="true"]` elements. Detects:
- Block types via CSS classes: `longform-header-one/two/three`, `longform-blockquote`, `longform-unordered-list-item`, `longform-ordered-list-item`
- Bold via `getComputedStyle` fontWeight >= 700
- Italic via fontStyle === 'italic'

**Output format:** `type|text` per line, with `§b§`/`§i§`/`§bi§` markers for inline formatting.

**Getting data out of the browser:** CSP blocks local fetches. Use `JSON.stringify(result)` in the evaluate return, then pipe through `node -e` or `python3 -c` via exec heredoc to write to files.

**Browser evaluate snippet:**
```js
() => {
  const root = document.querySelector('.DraftEditor-root');
  if (!root) return 'NO_ROOT';
  const blocks = root.querySelectorAll('[data-block="true"]');
  const result = [];
  for (const block of blocks) {
    const cls = block.className || '';
    let type = 'p';
    if (cls.includes('longform-header-one')) type = 'h1';
    else if (cls.includes('longform-header-two')) type = 'h2';
    else if (cls.includes('longform-header-three')) type = 'h3';
    else if (cls.includes('longform-blockquote')) type = 'bq';
    else if (cls.includes('longform-unordered-list-item')) type = 'ul';
    else if (cls.includes('longform-ordered-list-item')) type = 'ol';
    const inner = block.querySelector('.public-DraftStyleDefault-block') || block;
    function extract(node) {
      if (node.nodeType === 3) return node.textContent;
      if (node.nodeType !== 1) return '';
      let t = '';
      for (const c of node.childNodes) t += extract(c);
      const cs = window.getComputedStyle(node);
      const bold = cs.fontWeight === 'bold' || parseInt(cs.fontWeight) >= 700;
      const italic = cs.fontStyle === 'italic';
      if (t && (node.getAttribute('data-text') === 'true')) {
        if (bold && italic) return '\u00a7bi\u00a7' + t + '\u00a7/bi\u00a7';
        if (bold) return '\u00a7b\u00a7' + t + '\u00a7/b\u00a7';
        if (italic) return '\u00a7i\u00a7' + t + '\u00a7/i\u00a7';
      }
      return t;
    }
    let fullText = '';
    for (const c of inner.childNodes) fullText += extract(c);
    result.push(type + '|' + fullText);
  }
  return JSON.stringify(result);
}
```
#### What Doesn't Work for X Articles

- `web_fetch` — X blocks it
- fxtwitter API — only returns preview text for articles, not full body
- nitter/xcancel — blocked or missing article content
- playwright-core via CDP — can't see DraftEditor (needs logged-in session context)
- Browser `fetch` to localhost — CSP blocks it

### Step 2: Save Raw Files

For each article, save:
- `/tmp/artN_raw.txt` — the `type|text` lines (join the JSON array with `\n`)
- `/tmp/artN_meta.json` — `{"title": "...", "author": "...", "handle": "@username", "bio": "One-line intro"}`

Use fxtwitter API (`api.fxtwitter.com/{user}/status/{id}`) for title/author metadata.
Use fxtwitter API (`api.fxtwitter.com/{username}`) for user bio/description.

For X posts, always include the `handle` (with @) and a short `bio` (one line intro of the author). The handle and bio appear under each article title. Escape `@` and `_` in handles for Typst (`\@`, `\_`).

### Step 3: Build PDF

```bash
python3 scripts/build_book.py --json /tmp/articles.json --title "Book Title" -o output.pdf
```

Or use `scripts/build_final.py` (at `/tmp/build_final.py`) which reads `artN_raw.txt` and `artN_meta.json` files directly.

The build script:
1. Parses `type|text` format
2. Converts `§b§`/`§i§` markers to Typst `*bold*`/`_italic_`
3. Escapes dangerous Typst chars (`\ # \` < > @ $ ~`) but preserves `*` and `_`
4. Generates complete `.typ` file with cover, TOC, and articles
5. Compiles via `typst compile`


## Cover Title

The cover title should summarize a unifying theme across all articles in the collection, not just say "Collected Readings." When building, either:
- Pass `--title "Your Theme Title"` to the build script
- Or have the agent read through the articles and generate a thematic title that captures the common thread

All individual authors are listed on the cover below the title.

## X Article Specifics

When the source is an X post/article:
- **Handle:** Always include the author's X handle (e.g. @thedankoe) under the article title
- **Author bio:** Fetch a one-line intro from the fxtwitter user API (`api.fxtwitter.com/{username}` → `user.description`). Clean it up to one short sentence if needed.
- **Format under each article title:**
  - Line 1: `By Author Name (@handle)` — 8.5pt italic, #555
  - Line 2: `Short bio` — 8pt regular, #888
- **Escaping handles in Typst:** `@` → `\@`, `_` → `\_`

## Layout

- **Paper:** A4 landscape (flipped)
- **Columns:** Two, with gap
- **Font:** Charter throughout

### Article Flow

Articles flow continuously without full page breaks. Each new article starts at the top of the next column using `#colbreak()` in Typst, which fills the blank column from the previous article and keeps the book compact.

### Type Hierarchy

| Element | Size | Weight | Color |
|---|---|---|---|
| Cover title | 28pt | Bold | Black |
| Cover authors | 12pt | Regular | #555 |
| TOC header | 16pt | Bold | Black |
| TOC entries | 10pt | Regular | Black |
| Article title (=) | 14pt | Medium | Black |
| Author + handle | 8.5pt | Regular italic | #555 |
| Author bio | 8pt | Regular | #888 |
| Section heading (==) | 10pt | Regular | Black |
| Sub-section (===) | 9.5pt | Regular | Black |
| Body text | 9pt | Regular, 0.6em leading | Black |
| Block quotes | 8.5pt | Regular italic, indented | #444 |
| Page numbers | 7pt | Regular | #999 |

Note: Headings use `#set text(weight: "regular")` inside show rules to neutralize inline bold markers from the source. This prevents double-bold when articles use bold text inside their headings.

## Requirements

- Python 3 (stdlib only)
- Typst (`/opt/homebrew/bin/typst`)
- OpenClaw browser tool (for X Article scraping)


## Currently Supported

- **X Articles** (long-form posts) — fully tested, formatting preserved
- **X tweets** (regular short posts) — via fxtwitter API
