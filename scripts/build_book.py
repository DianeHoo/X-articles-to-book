#!/usr/bin/env python3
"""Build a PDF book from URLs or JSON article data."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
TYPST_BIN = "/opt/homebrew/bin/typst"


def escape_typst_string(s):
    """Escape a string for use inside Typst quoted strings."""
    return s.replace('\\', '\\\\').replace('"', '\\"')


def escape_typst_content(s):
    """Escape special chars in Typst content mode (preserves * and _ for formatting)."""
    for ch in ['\\', '#', '`', '<', '>', '@', '$', '~']:
        s = s.replace(ch, '\\' + ch)
    return s


def body_to_typst_content(text, raw=False):
    """Convert text body to Typst content-mode markup.
    
    If raw=True, the text is already Typst-formatted (from scraper) and is
    inserted as-is without escaping.
    """
    if raw:
        return text
    lines = text.split('\n')
    out = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            out.append('')  # blank line = paragraph break in Typst
            continue
        # Detect markdown-style headings
        heading_level = 0
        for i in range(4, 0, -1):
            prefix = '=' * i + ' '
            if stripped.startswith(prefix):
                heading_level = i
                stripped = stripped[len(prefix):]
                break
        if heading_level:
            # Map to level 2+ (level 1 is article title)
            typst_level = '=' * (min(heading_level, 2) + 1)
            out.append(f"{typst_level} {escape_typst_content(stripped)}")
        else:
            out.append(escape_typst_content(stripped))
    return '\n'.join(out)


def build_typ_source(title, authors, articles):
    """Generate complete standalone .typ source with articles as direct content."""
    today = date.today().strftime("%B %d, %Y")
    
    # We need article count for TOC logic
    show_toc = len(articles) > 1

    parts = []
    
    # Cover page
    parts.append(f'''// Generated book — landscape two-column layout
// ── Cover page ──────────────────────────────────────────────
#set page(paper: "a4", flipped: true)
#page(margin: (x: 1.5in, y: 2in), columns: 1, header: none, footer: none)[
  #align(center + horizon)[
    #block(spacing: 0.6em)[
      #text(size: 28pt, weight: "bold", font: "Charter", "{escape_typst_string(title)}")
    ]
    #v(0.4in)
    #text(size: 14pt, fill: rgb("#555"), font: "Charter", "{escape_typst_string(authors)}")
    #v(0.3in)
    #text(size: 11pt, fill: rgb("#888"), "{today}")
  ]
]

// ── Document settings ───────────────────────────────────────
#set page(
  paper: "a4",
  flipped: true,
  margin: 0.75in,
  columns: 2,
  footer: context {{
    let num = counter(page).get().first()
    align(center, text(size: 8pt, fill: rgb("#999"), str(num)))
  }},
)

#set text(font: "Charter", size: 9pt)
#set par(leading: 0.6em, first-line-indent: 0em, justify: true)
#show heading.where(level: 1): it => {{
  colbreak(weak: true)
  v(0.3in)
  text(font: "Helvetica Neue", size: 16pt, weight: "bold", it.body)
  v(0.15in)
}}
#show heading.where(level: 2): it => {{
  v(0.15in)
  text(font: "Helvetica Neue", size: 12pt, weight: "bold", it.body)
  v(0.08in)
}}
''')

    # TOC
    if show_toc:
        parts.append('''// ── Table of Contents ───────────────────────────────────────
#heading(level: 1, outlined: false)[Contents]
#outline(title: none, indent: 1em, depth: 1)
#colbreak()
''')

    # Articles as direct content
    parts.append('// ── Articles ────────────────────────────────────────────────')
    for a in articles:
        art_title = escape_typst_content(a.get('title', 'Untitled'))
        author = a.get('author', '')
        is_raw = a.get('body_raw', False)
        body = body_to_typst_content(a.get('body', ''), raw=is_raw)
        
        parts.append(f'\n= {art_title}')
        if author:
            parts.append(f'#text(size: 9pt, fill: rgb("#666"), style: "italic")[By {escape_typst_content(author)}]')
            parts.append('#v(0.12in)')
        parts.append('')
        parts.append(body)
        parts.append('')

    return '\n'.join(parts)


def main():
    parser = argparse.ArgumentParser(description="Build a PDF book from articles")
    parser.add_argument('urls', nargs='*', help='URLs to fetch')
    parser.add_argument('--title', default='Collected Readings', help='Book title')
    parser.add_argument('--author', '--authors', default='', help='Author(s)')
    parser.add_argument('--output', '-o', default='book.pdf', help='Output PDF path')
    parser.add_argument('--json', dest='json_file', help='JSON file with articles instead of URLs')
    parser.add_argument('--sample', action='store_true', help='Generate sample book')
    args = parser.parse_args()

    articles = []

    if args.sample:
        articles = [
            {
                'title': 'The Art of Deep Work',
                'author': 'Cal Newport',
                'body': (
                    "Deep work is the ability to focus without distraction on a cognitively demanding task. "
                    "It's a skill that allows you to quickly master complicated information and produce better "
                    "results in less time. In an increasingly connected world, the ability to perform deep work "
                    "is becoming both rare and valuable.\n\n"
                    "The key to developing a deep work practice is to move beyond good intentions and add routines "
                    "and rituals designed to minimize the amount of willpower necessary to transition into and "
                    "maintain a state of unbroken concentration. The goal is not to impose monastic isolation, "
                    "but rather to develop a thoughtful approach to scheduling deep work.\n\n"
                    "Professional activities performed in a state of distraction-free concentration push your "
                    "cognitive capabilities to their limit. These efforts create new value, improve your skill, "
                    "and are hard to replicate. This is exactly the type of work that moves the needle."
                )
            },
            {
                'title': 'On the Shortness of Life',
                'author': 'Seneca',
                'body': (
                    "It is not that we have a short time to live, but that we waste a great deal of it. Life is "
                    "long enough, and a sufficiently generous amount has been given to us for the highest "
                    "achievements if it were all well invested. But when it is wasted in heedless luxury and "
                    "spent on no good activity, we are forced at last by death's final constraint to realize "
                    "that it has passed away before we knew it was passing.\n\n"
                    "People are frugal in guarding their personal property; but as soon as it comes to squandering "
                    "time they are most wasteful of the one thing in which it is right to be stingy. You act like "
                    "mortals in all that you fear, and like immortals in all that you desire.\n\n"
                    "It is not that we have so little time but that we lose so much. The life we receive is not "
                    "short but we make it so; we are not ill-provided but use what we have wastefully."
                )
            },
            {
                'title': 'Walking and Creativity',
                'author': 'Rebecca Solnit',
                'body': (
                    "The rhythm of walking generates a rhythm of thinking, and the passage through a landscape "
                    "echoes or stimulates the passage through a series of thoughts. This creates an odd consonance "
                    "between internal and external passage, one that suggests that the mind is also a landscape "
                    "of sorts and that walking is one way to traverse it.\n\n"
                    "Many great thinkers and writers have found that walking unlocks their creative process. "
                    "Wordsworth composed while walking the Lake District. Dickens walked twenty miles through "
                    "London at night. Nietzsche declared that only thoughts conceived while walking have any value.\n\n"
                    "The walking body is not merely transport for the thinking mind. The two are intertwined in "
                    "ways we are only beginning to understand. When we walk, the world comes to us through our "
                    "senses in a steady, rhythmic flow that seems to synchronize with the flow of thought itself."
                )
            },
        ]
    elif args.json_file:
        with open(args.json_file) as f:
            articles = json.load(f)
    elif args.urls:
        sys.path.insert(0, SCRIPT_DIR)
        from fetch_content import fetch_article
        for url in args.urls:
            result = fetch_article(url)
            if result:
                articles.append(result)
            else:
                print(f"Warning: Could not fetch {url}", file=sys.stderr)
    else:
        urls = [line.strip() for line in sys.stdin if line.strip()]
        if urls:
            sys.path.insert(0, SCRIPT_DIR)
            from fetch_content import fetch_article
            for url in urls:
                result = fetch_article(url)
                if result:
                    articles.append(result)

    if not articles:
        print("Error: No articles to build book from.", file=sys.stderr)
        sys.exit(1)

    authors = args.author
    if not authors:
        unique = list(dict.fromkeys(a.get('author', '') for a in articles if a.get('author')))
        authors = ', '.join(unique) if unique else 'Various Authors'

    typ_source = build_typ_source(args.title, authors, articles)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.typ', delete=False) as f:
        f.write(typ_source)
        typ_path = f.name

    try:
        output_path = os.path.abspath(args.output)
        result = subprocess.run(
            [TYPST_BIN, 'compile', typ_path, output_path],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"Typst error:\n{result.stderr}", file=sys.stderr)
            debug_path = output_path.replace('.pdf', '.typ')
            os.rename(typ_path, debug_path)
            print(f"Source saved to {debug_path} for debugging", file=sys.stderr)
            sys.exit(1)
        print(output_path)
    finally:
        if os.path.exists(typ_path):
            os.unlink(typ_path)


if __name__ == '__main__':
    main()
