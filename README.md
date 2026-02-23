# articles-to-book

Turn web articles into beautifully formatted two-column PDF books.

## What it does

Give the agent one or more article URLs, and it will:
1. Scrape the full content with formatting preserved (bold, italic, headings, quotes, lists)
2. Generate a thematic cover title based on the collection
3. Build a landscape PDF with cover, table of contents, and all articles

## What you need

- [Typst](https://typst.app) installed (`brew install typst`)
- Python 3
- For X Articles: a browser session logged into X (the agent uses browser automation to scrape)

## Currently supported

- **X Articles** (long-form posts) — fully tested, formatting preserved
- **X tweets** (regular short posts)

Other sources (Medium, WeChat, generic web) are planned but not yet tested.

## License

MIT
