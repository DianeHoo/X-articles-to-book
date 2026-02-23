#!/usr/bin/env python3
"""Build the final PDF from scraped article data."""
import json, re, os, subprocess, sys
from datetime import date

def parse_raw_to_typst(text):
    """Convert raw block format (type|text) to Typst markup."""
    lines = text.strip().split('\n')
    out = []
    for line in lines:
        if '|' not in line:
            out.append('')
            continue
        btype, content = line.split('|', 1)
        # Convert formatting markers
        content = re.sub(r'§bi§(.*?)§/bi§', r'*_\1_*', content)
        content = re.sub(r'§b§(.*?)§/b§', r'*\1*', content)
        content = re.sub(r'§i§(.*?)§/i§', r'_\1_', content)
        # Escape dangerous Typst chars (not * and _)
        safe = ''
        for ch in content:
            if ch == '\\': safe += '\\\\'
            elif ch == '#': safe += '\\#'
            elif ch == '`': safe += '\\`'
            elif ch == '<': safe += '\\<'
            elif ch == '>': safe += '\\>'
            elif ch == '@': safe += '\\@'
            elif ch == '$': safe += '\\$'
            elif ch == '~': safe += '\\~'
            else: safe += ch
        content = safe
        
        if btype in ('h1', 'h2'):
            out.append('')
            out.append(f'== {content}')
            out.append('')
        elif btype == 'h3':
            out.append(f'=== {content}')
            out.append('')
        elif btype == 'bq':
            out.append(f'#quote[{content}]')
            out.append('')
        elif btype == 'ul':
            out.append(f'- {content}')
        elif btype == 'ol':
            out.append(f'+ {content}')
        else:
            out.append(content)
            out.append('')
    
    result = '\n'.join(out)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()

def escape_typst_string(s):
    return s.replace('\\', '\\\\').replace('"', '\\"')

# Load articles
articles = []
for i in range(1, 6):
    raw_path = f'/tmp/art{i}_raw.txt'
    meta_path = f'/tmp/art{i}_meta.json'
    if not os.path.exists(raw_path):
        print(f"Missing {raw_path}, skipping")
        continue
    with open(raw_path) as f:
        raw = f.read()
    with open(meta_path) as f:
        meta = json.load(f)
    body = parse_raw_to_typst(raw)
    articles.append({'title': meta['title'], 'author': meta['author'], 'handle': meta.get('handle', ''), 'bio': meta.get('bio', ''), 'body': body})
    print(f"  Article {i}: {meta['title'][:50]}... ({len(body)} chars)")

# Generate Typst source
today = date.today().strftime("%B %d, %Y")

# Generate thematic title from article titles
book_title = sys.argv[sys.argv.index('--title') + 1] if '--title' in sys.argv else None
if not book_title:
    # Auto-generate from content themes
    book_title = "Collected Readings"

authors_list = ", ".join(a['author'] for a in articles)

parts = []

# Cover page
parts.append(f'''// Generated book
#set page(paper: "us-letter", flipped: true)
#page(margin: (x: 1.5in, y: 2in), columns: 1, header: none, footer: none)[
  #align(center + horizon)[
    #block(spacing: 0.6em)[
      #text(size: 28pt, weight: "bold", font: "Charter", "{escape_typst_string(book_title)}")
    ]
    #v(0.4in)
    #text(size: 12pt, fill: rgb("#555"), font: "Charter", "{escape_typst_string(authors_list)}")
    #v(0.3in)
    #text(size: 11pt, fill: rgb("#888"), "{today}")
  ]
]
''')

# Document settings
parts.append('''
// ── Document settings ──
#set text(font: "Charter", size: 9pt)
#set par(leading: 0.6em, first-line-indent: 0em, justify: true)
#set page(
  paper: "us-letter",
  flipped: true,
  margin: 0.75in,
  columns: 2,
  footer: context [
    #align(center)[
      #text(size: 7pt, fill: rgb("#999"))[#counter(page).display()]
    ]
  ]
)
#set heading(numbering: none)

// Article title (level 1 heading)
#show heading.where(level: 1): it => [
  #v(0.2in)
  #set text(weight: "regular")
  #text(size: 14pt, weight: "medium", font: "Charter")[#it.body]
  #v(0.06in)
]

// Section heading within article (level 2)
#show heading.where(level: 2): it => [
  #v(0.12in)
  #set text(weight: "regular")
  #text(size: 10pt, weight: "regular", font: "Charter")[#it.body]
  #v(0.04in)
]

// Sub-section heading (level 3)
#show heading.where(level: 3): it => [
  #v(0.08in)
  #set text(weight: "regular")
  #text(size: 9.5pt, weight: "regular", font: "Charter")[#it.body]
  #v(0.03in)
]

// Block quotes
#show quote: it => [
  #v(0.06in)
  #block(inset: (left: 0.2in, right: 0.1in))[
    #text(size: 8.5pt, style: "italic", fill: rgb("#444"))[#it.body]
  ]
  #v(0.06in)
]
''')

# TOC
parts.append('''
// ── Table of Contents ──
#page(columns: 1)[
  #align(center)[#text(size: 16pt, weight: "bold", font: "Charter")[Contents]]
  #v(0.3in)
''')
for i, art in enumerate(articles):
    safe_title = escape_typst_string(art['title'])
    safe_author = escape_typst_string(art['author'])
    parts.append(f'  #text(size: 10pt)[{i+1}. "{safe_title}" — {safe_author}]\n  #v(0.12in)')
parts.append(']\n')

# Articles
for art in articles:
    safe_title = escape_typst_string(art['title'])
    safe_author = escape_typst_string(art['author'])
    handle = art.get('handle', '')
    bio = art.get('bio', '')
    author_line = f"By {safe_author}"
    if handle:
        safe_handle = handle.replace('@', '\\@').replace('_', '\\_')
        author_line += f" ({safe_handle})"
    parts.append(f'''
// ── Article ──
= {safe_title}
#text(size: 8.5pt, fill: rgb("#555"), style: "italic")[{author_line}]
''')
    if bio:
        parts.append(f'#v(0.02in)\n#text(size: 8pt, fill: rgb("#888"))[{escape_typst_string(bio)}]')
    parts.append(f'''#v(0.1in)

{art['body']}

#pagebreak()
''')

typ_source = '\n'.join(parts)

# Write and compile
typ_path = '/tmp/collected_readings.typ'
with open(typ_path, 'w') as f:
    f.write(typ_source)
print(f"\nWrote {len(typ_source)} chars to {typ_path}")

pdf_path = os.path.expanduser('~/Downloads/collected-readings.pdf')
result = subprocess.run(
    ['/opt/homebrew/bin/typst', 'compile', typ_path, pdf_path],
    capture_output=True, text=True
)
if result.returncode != 0:
    print(f"Typst error:\n{result.stderr}")
    # Save error context
    lines = typ_source.split('\n')
    for m in re.finditer(r'line (\d+)', result.stderr):
        ln = int(m.group(1))
        print(f"\nAround line {ln}:")
        for j in range(max(0,ln-3), min(len(lines),ln+3)):
            print(f"  {j+1}: {lines[j][:100]}")
    sys.exit(1)
else:
    print(f"PDF compiled: {pdf_path}")
    os.system(f'open "{pdf_path}"')
