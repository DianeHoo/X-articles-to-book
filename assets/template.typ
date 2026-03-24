// Book template — landscape two-column layout
// Variables are injected at the top of the generated .typ file:
//   #let book-title = "..."
//   #let book-authors = "..."
//   #let book-date = "..."
//   #let articles = ((title: "...", author: "...", body: "..."), ...)

// ── Cover page ──────────────────────────────────────────────
#set page(paper: "a4", flipped: true)
#page(margin: (x: 1.5in, y: 2in), columns: 1, header: none, footer: none)[
  #align(center + horizon)[
    #block(spacing: 0.6em)[
      #text(size: 28pt, weight: "bold", font: "Charter", book-title)
    ]
    #v(0.4in)
    #text(size: 14pt, fill: rgb("#555"), font: "Charter", book-authors)
    #v(0.3in)
    #text(size: 11pt, fill: rgb("#888"), book-date)
  ]
]

// ── Document settings ───────────────────────────────────────
#set page(
  paper: "a4",
  flipped: true,
  margin: 0.75in,
  columns: 2,
  footer: context {
    let num = counter(page).get().first()
    align(center, text(size: 8pt, fill: rgb("#999"), str(num)))
  },
)

#set text(font: "Charter", size: 9pt)
#set par(leading: 0.6em, first-line-indent: 0em, justify: true)
#show heading.where(level: 1): it => {
  colbreak(weak: true)
  v(0.3in)
  text(font: "Helvetica Neue", size: 16pt, weight: "bold", it.body)
  v(0.15in)
}
#show heading.where(level: 2): it => {
  v(0.15in)
  text(font: "Helvetica Neue", size: 12pt, weight: "bold", it.body)
  v(0.08in)
}

// ── Table of Contents ───────────────────────────────────────
#if articles.len() > 1 {
  heading(level: 1, outlined: false)[Contents]
  outline(title: none, indent: 1em, depth: 1)
  colbreak()
}

// ── Articles ────────────────────────────────────────────────
#for (i, article) in articles.enumerate() {
  heading(level: 1, article.title)
  if article.author != "" {
    text(size: 9pt, fill: rgb("#666"), style: "italic")[By #article.author]
    v(0.12in)
  }
  eval(article.body, mode: "markup")
}
