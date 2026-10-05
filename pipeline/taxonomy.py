"""Grid taxonomy shared by the workflows and the page builder. Items and purposes follow ACCEPTANCE §§2–3."""

TOOLS = [
    {"id": "gdoc", "name": "gdoc", "interface": "CLI", "pin": "0.22.0 · 9343b35"},
    {"id": "taylor", "name": "Taylor's MCP", "interface": "MCP", "pin": "v1.26.0 · 54b1c56"},
    {"id": "gog", "name": "gog", "interface": "CLI", "pin": "v0.35.0 · 402def5"},
]
PURPOSES = [
    ("read", "Read", "Return the requested content and properties with their relationships intact; identify missing information."),
    ("select", "Select", "Identify the intended item using document concepts and distinguish multiple candidates."),
    ("wording", "Change wording", "Change the requested characters while retaining structural roles, unaffected formatting, links, references and other work."),
    ("format", "Change formatting", "Change only the requested properties on the selected items."),
    ("create", "Create", "Produce the requested item with native behavior, in the requested location."),
    ("restructure", "Restructure", "Move, split, join, nest, reorder, insert or delete structure while retaining content and relationships outside the change."),
    ("preserve", "Preserve", "Retain content, properties and relationships of items outside the requested change."),
    ("publish", "Publish Markdown", "Create a document from Markdown with native headings, lists, tables, links, code, quotes, images, footnotes and tabs."),
    ("update", "Update from Markdown", "Apply local Markdown changes while retaining direct edits, review items and objects absent from the source."),
    ("suggest", "Suggest", "Leave a pending reviewable suggestion; inspect, accept or reject suggestions."),
    ("discuss", "Discuss", "Read, create, reply to, resolve, reopen or delete comment threads attached to content or the whole document."),
    ("manage", "Manage files and access", "Find, copy, rename, move, organize, export and share documents with the intended audience and role."),
]
ITEMS = [
    ("range", "Text range", "Text and structure"), ("paragraph", "Paragraph", "Text and structure"),
    ("heading", "Heading", "Text and structure"), ("section", "Section", "Text and structure"),
    ("list", "List item", "Text and structure"), ("table", "Table and cell", "Text and structure"),
    ("tab", "Tab", "Text and structure"), ("link", "Link and bookmark", "Text and structure"),
    ("image", "Image", "Embedded objects"), ("equation", "Equation", "Embedded objects"),
    ("chip", "Smart chip", "Embedded objects"), ("drawing", "Drawing", "Embedded objects"),
    ("chart", "Chart", "Embedded objects"), ("unknown", "Unrecognized object", "Embedded objects"),
    ("footnote", "Footnote", "Regions and layout"), ("headerfooter", "Header or footer", "Regions and layout"),
    ("layout", "Page and section layout", "Regions and layout"), ("toc", "Table of contents", "Regions and layout"),
    ("comment", "Comment thread", "Review items"), ("suggestion", "Suggestion", "Review items"),
    ("file", "Document file", "Files and access"), ("access", "Sharing and access", "Files and access"),
]
ALL = [i[0] for i in ITEMS[:20]]
APPLICABLE = {
    "read": ALL + ["file", "access"],
    "select": ["range", "paragraph", "heading", "section", "list", "table", "tab", "comment", "suggestion", "file"],
    "wording": ["paragraph", "heading", "list", "table", "footnote", "headerfooter"],
    "format": ["range", "paragraph", "heading", "list", "table", "image", "layout"],
    "create": ["paragraph", "heading", "list", "table", "tab", "link", "image", "equation", "chip", "drawing", "chart", "footnote", "headerfooter", "toc", "comment", "suggestion", "file"],
    "restructure": ["paragraph", "heading", "section", "list", "table", "tab"],
    "preserve": ALL,
    "publish": ["range", "paragraph", "heading", "list", "table", "link", "image", "footnote", "tab"],
    "update": ALL,
    "suggest": ["range", "paragraph", "heading", "list", "table", "footnote", "suggestion"],
    "discuss": ["range", "paragraph", "heading", "table", "image", "comment"],
    "manage": ["file", "access"],
}
VARIATIONS = [
    ("repeated", "Repeated wording", "Content"), ("unicode", "Emoji or non-Latin text", "Content"),
    ("whitespace", "Literal whitespace or code", "Content"), ("long-doc", "Long document", "Content"),
    ("nested-tab", "Nested or non-first tab", "Location"), ("in-cell", "Inside a table cell", "Location"),
    ("in-footnote", "Inside a footnote", "Location"), ("in-header", "Inside a header or footer", "Location"),
    ("merged", "Merged or empty cells", "Structure"), ("nested-list", "Nested list", "Structure"),
    ("restart", "Numbering restart", "Structure"), ("incoming-link", "Linked text or incoming link", "Structure"),
    ("comment", "Attached comment", "Review"), ("suggestion", "Pending suggestion", "Review"),
    ("concurrent", "Collaborator edits concurrently", "Concurrent work"),
    ("lost-response", "Lost response or retry", "Failure timing"),
    ("read-only", "Limited access", "Access"), ("multi-doc", "Several documents", "Access"),
]


ITEM_HINTS = {
    "range": "words or phrases within a paragraph, including inline formatting runs",
    "paragraph": "ordinary body paragraphs",
    "heading": "headings and their level/outline position",
    "section": "a heading plus the content up to the next heading of equal or higher level",
    "list": "bulleted, numbered and checklist items with nesting",
    "table": "tables, rows, columns, cells, merged cells",
    "tab": "document tabs, nested tabs",
    "link": "hyperlinks, links to headings, bookmarks",
    "image": "inline and positioned images",
    "equation": "native equations",
    "chip": "person, file and date chips",
    "drawing": "inserted drawings",
    "chart": "charts linked to Sheets",
    "unknown": "objects a tool cannot interpret",
    "footnote": "footnote references and bodies",
    "headerfooter": "headers and footers",
    "layout": "page breaks, section breaks, margins, orientation, columns, pageless mode",
    "toc": "native table of contents",
    "comment": "comments, replies, resolution state, attachment",
    "suggestion": "pending suggested edits",
    "file": "the document as a Drive file: name, folder, copies, exports, metadata, revisions",
    "access": "who can view, comment or edit; link sharing",
}
