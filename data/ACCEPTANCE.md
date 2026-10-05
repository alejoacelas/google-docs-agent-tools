# Gdoc acceptance checks

Draft for review · 2026-10-01.

Gdoc should let people use agents to read, edit, review and publish Google Docs without losing existing work. This document describes the behavior we want and how we would recognize a correct result. It is intended to be read from beginning to end without another document open.

The lists below are **proposed required coverage**, not claims about what already works. They are independent of the current implementation and available tools. When reviewing, ask whether the listed capabilities, preservation promises and failure behavior are what you want. Questions that still need a product decision are stated beside the affected behavior.

A narrow live pilot has exercised selected checks. Most obligations remain untested. The review website design adds proposed quality measures without changing these desired outcomes.

## 1. How the checks fit together

Each check describes a **starting situation**, a **requested action**, an **expected result**, and **what must remain unchanged**. Its final paragraph explains how we would check the result.

We reuse named groups rather than repeating every property in every check. For example, **text formatting** means the explicitly listed properties below. A promise to preserve text formatting refers to that whole list, not just the bold or italic property used in an example.

A general promise applies to every item named in its coverage list. An example illustrates a particular case; it does not narrow the promise. Changing a heading's wording is one example of changing text, and the same preservation rule also applies to text in list items, cells and footnotes.

A check passes only when the requested result and the applicable preservation and reporting promises hold. A refusal can protect the document while leaving the requested task unfinished. A correct result with inadequate evidence remains unverified.

### Terms used throughout

| Term | Meaning |
| --- | --- |
| Caller | The person or agent asking gdoc to do something |
| Target | The specific text, object or region selected for an action |
| Scope | The document regions within which a read, search or change is requested |
| Native content | Content that behaves as its corresponding Google Docs item: a heading appears in the outline, a table is editable by cell, and a suggestion can be accepted or rejected |
| Preserved | Content, properties and relationships remain intact except for the requested changes and separately approved consequences |
| Authorized effects | The requested change plus any additional effects explicitly approved after disclosure; an instruction to update a document does not authorize unrelated loss or public exposure |
| Identity | An existing item remains the same item for callers and references that point to it; identical replacement text alone does not establish this |
| Block | A structural content unit, such as a paragraph, list item or table |
| Section | Proposed meaning: a heading and subsequent content up to, but excluding, the next heading of equal or higher level in the same tab and region |

**Choice for review:** Confirm the section definition. It determines what moves or disappears when a caller selects a whole section, rather than only its heading.

## 2. What the document contains

These named lists supply the vocabulary for the rest of the checks. Properties are things we can observe about document behavior or appearance; they do not prescribe a data model or API.

### Text and paragraph properties

**Text content** includes characters, their order, paragraph boundaries, and literal spaces, tabs and line breaks where they are part of the content.

**Text formatting** includes bold, italic, underline, strikethrough, subscript, superscript, font, font size, foreground color and highlight. We check both the value and which characters it applies to.

**Paragraph properties** include named style, heading level when applicable, alignment, indentation, spacing and text direction. **Links and embedded references** are tracked separately: changing a word must not silently redirect its link or detach a nearby footnote reference.

### Document items

| Item | What we need to distinguish and preserve when it is not being changed |
| --- | --- |
| Text range | Text content, text formatting, links, embedded references and containing paragraph |
| Paragraph | Its text ranges, paragraph properties and place in the document |
| Heading | Paragraph properties plus heading identity, level, outline position and section membership |
| Section | Its heading, ordered content, subsections, end boundary and containing tab/region |
| List item | Content, list membership, nesting, descendants, marker style, numbering continuation/restart and checked state |
| Table and cell | Rows, columns, cell positions and merged spans; cell content; widths, minimum heights, padding, alignment, fills and borders |
| Tab | Identity, title, parent tab, order, descendants, content and incoming references |
| Link and bookmark | Displayed link text, destination, bookmark location and behavior when followed |
| Image | Actual visual content, alternative text, dimensions, crop, rotation, wrapping and placement |
| Equation | Mathematical structure, position and ability to edit it as an equation |
| Smart chip | Type, displayed value and referenced person, file or date; the corresponding chip interaction |
| Drawing | Visual content, individual shapes and labels, positions, connectors and element identity |
| Chart | Visual content, labels, units, data series/values and any relationship to source data |
| Unrecognized object | Its presence and location, surrounding content boundaries, and identity where observable |
| Footnote | Reference location, associated note body and the content/formatting of that body |
| Header or footer | Content and the sections and first-page/odd/even page variants to which it applies |
| Page and section layout | Breaks, page mode, size, orientation, margins and columns |
| Table of contents | Entries, hierarchy, included heading levels and destinations |
| Comment thread | Messages in order, authors, timestamps, resolution state and actual attachment or document-level status |
| Suggestion | Proposed effects, affected content, attribution and pending/accepted/rejected state |

We use five shorter group names:

- **Text containers:** paragraphs, headings, list items, and paragraphs inside table cells, footnotes, headers and footers.
- **Embedded objects:** images, equations, smart chips, drawings, charts and unrecognized objects.
- **Review items:** comment threads and suggestions.
- **Document regions:** tab bodies, footnote bodies, headers and footers. Tabs can be nested.
- **Document items:** all rows of the table above, including their contents and relationships.

Relationships matter independently of visible content. A paragraph can contain text, have a comment attached to it and be reached by a bookmark. Moving it changes its location; it should retain the associations and references we promised to preserve.

**Choices for review:** The drawing, chart and chip lists need a final scope decision. The proposed checks cover editable shapes/text/connectors, chart content and source refresh, and person/file/date chips. Other chip types, drawing properties and chart-editing actions are not yet fully specified. Existing objects remain protected even when authoring them is outside the selected scope.

## 3. What each kind of support means

Reading an item, creating it and preserving it during another edit are separate promises. An image might be readable even while creation remains unmet. An existing object still needs preservation even if gdoc cannot create it.

| Purpose | Items covered | Required outcome for each listed item |
| --- | --- | --- |
| Read | Document items within the requested scope | Return the requested content and properties with their relationships intact. Identify missing information; do not invent the meaning of unrecognized objects. |
| Select | Text ranges, paragraphs, headings, sections, list items, tables, cells, tabs and review items | Identify the intended item using document concepts and distinguish multiple candidates. |
| Change wording | Text containers | Change the requested characters while retaining structural roles, unaffected formatting, links, references and other work. |
| Change formatting | Text and paragraph properties; list, table, image and page-layout properties listed above | Change only the requested properties on the selected items. |
| Create | Paragraphs, headings, lists, tables, tabs, links, bookmarks, images, equations, chips, drawings, charts, footnotes, headers/footers, tables of contents and review items | Produce the requested item with the corresponding native behavior, in the requested location. |
| Restructure | Paragraphs, blocks/sections, list subtrees, tables and tab hierarchies | Perform the particular structural actions listed in the next section, retaining content and relationships outside the authorized change. |
| Preserve during another change | All document items outside authorized effects | Retain their content, properties and relationships, including items gdoc cannot author. |
| Publish Markdown | Paragraphs, headings, emphasis, links, lists, tables, code, quotes, images, footnotes and tab hierarchy | Produce the intended content, native structures and agreed presentation. |
| Update from Markdown | Changed source content and all retained document items | Apply intended source changes while retaining other work, including direct document edits and objects absent from the source format. |
| Suggest changes | Text insertion, deletion, replacement and formatting changes | Leave a pending reviewable change; acceptance and rejection produce their respective intended outcomes. |
| Discuss content | Selected content and explicitly document-level discussion | Create the requested attachment or document-level comment and retain the thread's identity through replies and state changes. |

**Choices for review:** Suggesting structural or object changes is not yet specified. Nor is the exact attachment granularity for comments on non-text objects. These remain open promises to define, not capabilities to infer from a successful text suggestion or comment.

## 4. Reading and choosing the intended content

A read returns the requested scope with its actual coverage visible. The caller can distinguish empty content from content that was omitted, denied, unavailable or not understood. A large read can be continued without unreported gaps or duplicates. If successive portions cannot be established as one consistent document state, that uncertainty is visible.

Text retains its characters and boundaries. Tables retain cell relationships, lists retain membership and nesting, and review items retain their state and connection to content. Reading a visual object includes inspectable visual content, not only an identifier or alternative text.

Selection works in document terms. Matching text across formatting runs finds the actual phrase. Repeated text or titles produce distinguishable candidates; a single-target mutation with zero or multiple matches changes nothing. An explicit all-match request accounts for every qualifying match within its scope, including matches returned across several responses. Matching choices such as case handling must be visible before writing.

### Example — read a merged table

**Starting situation:** A three-row, three-column table has its first two cells in row one merged. The merged cell contains “Overview”; the third cell is empty. Row two contains “A”, a two-item native list, and “C”. Row three contains “D”, “E”, and “F”.

**Requested action:** Read this table with its structure and formatting.

**Expected result:** The caller can reconstruct the three rows, three columns, merged span, empty cell and ordered content. The list is identifiable as a list inside its cell. The document remains unchanged.

**How we check:** Compare the returned information with the known starting table. Returning all the words in a flattened string does not satisfy the check.

### Example — choose among repeated phrases

**Starting situation:** “Draft” occurs in two tabs and two table cells. The caller asks to change one occurrence but has not said which.

**Requested action:** Attempt the edit, then choose one of the returned candidates. Before that chosen edit executes, another person inserts an earlier occurrence of “Draft”.

**Expected result:** The ambiguous attempt changes nothing and returns recognizable locations. The later attempt changes the originally chosen occurrence or explains that the selection can no longer be established. It never silently edits the newly inserted occurrence.

**How we check:** Compare the locations and content before and after, including the information shown to the caller. Separately request all matches in one tab and confirm that all of them—and none in other tabs—are covered. Refusing a stale selection can protect the document while leaving the edit unfinished.

**Choices for review:** Default read scope, inclusion of open/resolved discussions and matching normalization remain to be selected. The explicit-scope promises above do not depend on those defaults.

## 5. Editing and restructuring existing work

The common preservation rule is: **only authorized effects may change.** For wording edits this includes retaining the item's structural role, unaffected text formatting, links, embedded references and review associations. If new words cannot be mapped unambiguously onto existing formatting or references, gdoc exposes the choice before writing.

The requested structural actions are:

| Item | Actions and their intended boundaries |
| --- | --- |
| Text and paragraphs | Insert, replace or delete selected characters; set or clear selected formatting; create paragraphs; split at a selected boundary; join with an explicit separator and resulting paragraph style |
| Headings and sections | Create headings; change heading level; move selected blocks or sections within/between tabs; distinguish heading-only deletion from section deletion |
| Blocks | Insert before/after a selected block or at a section boundary; replace a selected block range without changing its neighbors |
| Lists | Create bullets, numbered items and checklists; insert items; nest/unnest a subtree by the requested levels; change markers, numbering or checked state; delete an item with an explicit choice about descendants |
| Tables | Create tables; edit a cell without changing geometry; insert/delete rows or columns; merge/split cells with explicit content placement; change selected layout properties |
| Tabs | Create, rename, reorder or reparent a tab subtree; delete the selected subtree with its losses disclosed; retain identity during rename/reorder |
| Links and bookmarks | Create/change a link destination; remove a link without removing its text; create a bookmark that continues to identify the intended location |
| Embedded objects | Create the specified native object; replace an image/equation/chip; change image presentation or individual drawing elements; refresh linked charts; delete only the selected object and authorized dependent references |
| Footnotes | Create the reference and body, edit the body, or delete the selected reference/body pair together |
| Layout and navigation | Edit the selected header/footer variant; change selected page/section properties; insert/remove breaks; create/refresh a table of contents with working destinations |

A move changes location and order but retains the selected content, internal relationships and associated work. A format change changes named properties but retains characters and other properties. A deletion removes the selected content and only its authorized dependent effects. Where additional loss is required, the caller sees it before deciding whether to authorize it.

If preservation cannot be established before writing, gdoc refuses the unsafe attempt. That refusal does not satisfy the desired editing capability.

### Example — change a reviewed heading

**Starting situation:** A level-two heading in a nested tab reads “Project status”. “Project” is linked and has a comment attached to it. Another tab contains an identical heading. The caller has unambiguously selected the first heading.

**Requested action:** Replace only “status” with “progress”.

**Expected result:** The selected heading reads “Project progress”. It remains a level-two heading with its existing paragraph properties and unaffected text formatting. “Project” retains its link and actual comment attachment. The other heading and everything else in the document remain unchanged.

**How we check:** Compare the document before and after, follow the link and inspect the comment attachment. The operation reports saving separately from verification. If attachment cannot be inspected, its preservation remains unknown rather than passed.

### Example — move a reviewed section

**Starting situation:** A level-two “Appendix” heading is followed by a commented paragraph, a pending wording suggestion and a nested list. The section ends before the next level-two heading. A link elsewhere points to “Appendix”.

**Requested action:** Move the section immediately after a selected heading in another tab.

**Expected result:** The whole section appears once at the destination, in its original internal order, and is absent from the source. Its contents, formatting, comment attachment, pending suggestion and incoming link survive. The neighbors at both locations remain intact.

**How we check:** Compare both locations, follow the link and inspect the review items. An unavailable move leaves this capability unmet.

**Choices for review:** Confirm the section boundary and treatment of references during cross-region moves. Also settle insertion formatting, split/join styles, list inheritance and content placement for geometry changes. A check can supply an explicit choice while defaults remain open; it must not silently choose one based on what the implementation happens to produce.

## 6. Comments and suggestions

Reading discussion returns the requested messages in order, with attribution, timestamps and resolution state. Comment locations distinguish actual attachment from inferred text matches, known detachment and unavailable evidence. Finding the old quoted words does not by itself prove a comment remains attached.

Callers can create an attached or explicitly document-level comment, reply to the selected thread, resolve/reopen it, or delete the selected discussion after its loss is disclosed. Similar threads must remain distinguishable. An unavailable attached comment cannot silently become a document-level comment.

Suggestions remain pending changes. Callers can inspect them, preview the document as if they were accepted or rejected without changing their state, and accept or reject the selected proposed effects. If those effects change after the caller reviews them, the old decision must not silently authorize the new effects. A direct edit never substitutes for a requested suggestion.

### Example — suggest wording near a footnote

**Starting situation:** “Cost is low” is followed by a footnote reference with a formatted note body. No pending suggestion affects the target.

**Requested action:** Suggest replacing “low” with “moderate”, without selecting the footnote reference.

**Expected result:** A pending replacement exists. Reads showing pending changes, an accepted preview and a rejected preview identify their interpretation and leave the actual suggestion state unchanged. Accepting the suggestion produces “Cost is moderate”; rejecting it retains “Cost is low”. Either decision preserves the reference, note body and unrelated work.

**How we check:** Inspect the pending state and test acceptance/rejection on separate copies of the starting document. Repeat with a suggestion inside the note body. Merely finding the new words does not establish that a reviewable suggestion was created.

## 7. Publishing and updating from Markdown

Publishing maps the named Markdown constructs to document outcomes: headings participate in the outline, lists and tables retain native editing behavior, links navigate correctly, images retain the supplied visual content, and footnotes retain their reference/body relationship. Code preserves literal characters, spaces, tabs and line breaks. Ordered source tabs become the requested native hierarchy.

Source constructs that cannot be interpreted without losing content or structure are identified before applying that lossy interpretation. Exact Markdown source spelling is not a fidelity goal; resulting content, structure and behavior are.

**Choice for review:** Agree the Markdown dialect and presentation rules for code, quotes, heading styles, lists, tables and whitespace. Code and quotations must be distinguishable from body text, but their precise presentation is not yet decided. We cannot accept a presentation-sensitive result until its expected appearance is defined.

An update applies the intended source changes while preserving unchanged document work, direct edits, review items and objects absent from the source format. Omission of a tab from supplied source does not delete it. Updating a tab preserves its identity. Replacement of a declared scope is a distinct action whose losses must be disclosed; preserving update cannot silently become replacement.

Extracted content retains information about which scope and document state it represents. A partial, historical or suggestion-preview read cannot masquerade as a current complete editing source. Writing extracted content to a local file must retain local edits made before or during extraction.

### Example — update a collaboratively edited document

**Starting situation:** The shared starting version contains “Budget: 10” and “Owner: Ada” in tab A. Local Markdown changes the budget to “12” and owner to “Bo”. Someone edits the document's budget to “11”, adds a reviewed paragraph and a drawing, and creates tab B, which is absent from the local source.

**Requested action:** Apply a preserving Markdown update. Inspect the conflicting budget changes, then explicitly choose “12”.

**Expected result:** Neither budget version wins silently. After resolution, the document contains “Budget: 12” and “Owner: Bo”. The added paragraph, its review discussion, the drawing and tab B remain. Tab A retains its identity.

**How we check:** Compare the shared starting version, both changed versions and the final document, including review and object relationships. Rebuilding tab A while losing its additions fails the check even if the two source sentences are correct.

**Choice for review:** Decide whether compatible concurrent changes are combined automatically, and whether nonconflicting changes may be applied before a conflict is resolved. Regardless of that choice, conflicts must remain visible and any partial effects must be reported.

## 8. Failure reporting and recovery

Every result identifies the account, document and affected scope. It distinguishes **saved effects**, **effects not sent**, and **effects whose outcome is unknown**. Verification is separate: the expected outcome may be confirmed, contradicted, or not established.

For grouped work, the caller learns whether changes are all-or-nothing or can finish separately before execution. An unavailable all-or-nothing guarantee is refused before writing. Partial completion identifies the individual completed, incomplete and uncertain effects. A later verification or local-state failure must not turn a confirmed save into a claim that nothing happened.

Recovery establishes what happened before repeating consequential actions. It retains confirmed effects, completes remaining work once their status is established, and preserves intervening edits. An early read that finds nothing does not establish that a delayed original request will never finish. Restoring an old snapshot must not erase work done after it was captured.

### Example — recover document creation after a lost response

**Starting situation:** The caller requests one new document containing “Recovery example”. Creation succeeds, but the response never reaches the caller.

**Requested action:** Restart and recover or retry that same creation request.

**Expected result:** The operation is not blindly repeated. Recovery identifies the created document or retains explicit uncertainty until evidence resolves the outcome. Once completed, exactly one document exists for the original request, under the selected account, with its content populated once.

**How we check:** Inspect the created documents independently of gdoc's response. Repeat with the original request delayed until after an early recovery inspection. Also interrupt a multi-step task and confirm that resumption performs only the established remaining work. A refusal that leaves creation unresolved protects against duplication but does not establish recovery completion.

**Choices for review:** Define how callers distinguish retrying the same intent from requesting another copy, and how long recovery remains available. These choices must be settled before claiming a recovery check covers restarts or elapsed time generally.

## 9. Accounts and authorized external effects

The selected account remains consistent across an operation and recovery. Observations and recovery state from one account cannot authorize another account's actions. Missing access is reported without silently switching identity.

Sharing changes affect only the authorized audience and role. Notification effects are disclosed before the action; a permission change does not prove that a recipient received a message or can actually access the document. Temporary exposure beyond the document's authorized audience requires explicit permission, and failed cleanup remains visible.

Feedback is previewed with its exact contents, destination and sending identity. Sending requires approval for that payload and destination. Telemetry collection policy remains undecided; these checks do not introduce collection.

### Example — insert an image without unapproved exposure

**Starting situation:** A local image has not been authorized for public exposure.

**Requested action:** Insert it into a document.

**Expected result:** Gdoc inserts it without unapproved exposure or reports that insertion remains unmet. Generic permission to insert the image does not authorize making it public.

**How we check:** Inspect both the document and any external access effects. In a separate explicitly authorized temporary-exposure case, induce cleanup failure: the caller must learn what remains exposed even if insertion succeeded.

### Example — retain the exact feedback approval

**Starting situation:** The caller approves a previewed diagnostic report and its named destination.

**Requested action:** Change the payload or destination, then attempt transmission using the old approval.

**Expected result:** The changed report is not sent without fresh approval. An uncertain earlier transmission is investigated rather than blindly resent.

**How we check:** Inspect the attempted and actual transmissions independently of the success message. These are synthetic test scenarios; the document does not authorize sending feedback or exposing content.

## 10. Interfaces and supporting tasks

The command-line interface and Model Context Protocol interface used by agent clients must give equivalent document effects and protections for equivalent requests. Both expose essential operation meanings, inputs, scope, uncertainty and recovery information without depending on a separate instruction file. Calls finish or return an unresolved decision without waiting for an interactive prompt.

Check human-readable and structured results, including errors and output limits. Document URLs and IDs select the same document. Command-line file, standard-input and inline content produce equivalent effects to agent-client inline content. Read-only and operation restrictions hold across all routes; an agent-client content argument must not expose or overwrite arbitrary files on the server.

Supporting tasks need their own outcome checks:

| Task | Expected outcome |
| --- | --- |
| Find documents | Find accessible documents by name and folder; distinguish same-named results and disclose incomplete listings |
| Read metadata | Return document identity, title, location and available access information without requiring a body read |
| Copy | Create a separate copy without modifying the source; retain the content and relationships selected by the copy policy |
| Rename or move | Retain document identity and content; moves retain authorized access or disclose required access changes first |
| Organize files | Create folders at the selected location and list accessible drives/folder contents; distinguish empty, denied and incomplete results |
| Export | Produce the requested format with its agreed content and scope fidelity |
| Automate | Expose skipped, refused, partial and unknown work rather than reporting task completion |
| Migrate callers | Identify incompatible requests instead of silently changing their operation meaning |

**Choices for review:** Select required export formats and their fidelity, copy treatment of comments/suggestions/permissions, and supported client versions. Concrete checks need these choices; a successful export in one format does not qualify the others.

## 11. How broadly to exercise these promises

Simple examples are not enough. The same named action must be checked across its required item list, including combinations where preservation is difficult.

| Variation | Cases to include |
| --- | --- |
| Content | Empty/populated items, repeated wording, mixed formatting and links, emoji, combining characters, right-to-left text and literal whitespace |
| Location | Main body, nested tab, cell, footnote, header/footer; start/middle/end of the selected container |
| Structure | Nested/adjacent lists, numbering restarts, merged/empty cells, duplicate titles and incoming links |
| Review | Attached/resolved threads, replies, pending text/formatting suggestions, inferred or unavailable attachment |
| Concurrent work | Unrelated edits, changed/deleted target, an earlier similar target inserted, edits between steps and during recovery |
| Failure timing | Before sending, uncertain response, confirmed save before verification, partial completion, restart and delayed completion |
| Access and client | Authorized/read-only/denied access, two accounts, operation restrictions, each supported client and content-input form |

For every item, check preservation while another part of the document is edited and while Markdown is updated. Include relationships crossing the changed region. Exercise each named formatting property independently, and every native variant such as bullet/number/checklist and person/file/date chip. Check wording changes in every text container.

The combinations illustrated above are mandatory examples, supplemented by nested lists with restarted numbering, merged tables with formatted cell content, and Markdown updates around objects absent from the source. Failure/recovery cases must cover content changes, review actions, creation, sharing and feedback separately; a recovered text edit does not establish recovered comment creation.

Not every conceivable combination needs a separate case. Record omitted applicable combinations and the evidence still missing. A property that has no meaning for an item—such as checked state on a heading—is inapplicable. A missing implementation route means an unmet promise, not an inapplicable check.

## 12. How we judge the result

Prepare exact starting documents and expected values independently of the implementation. Keep intended changes and protected properties explicit. Inspect the resulting document and caller-visible response; use native interaction when needed to establish editing, navigation or review behavior.

A screenshot can show appearance but cannot alone establish native editability, comment attachment or complete preservation. A raw before/after response comparison can include irrelevant internal differences. Compare the content, properties, identities and relationships promised here. Define any numerical or visual tolerance before observing the result; do not invent one to excuse a mismatch.

Record the requested capability, preservation and reporting results separately. Each observation is **passed**, **failed**, **unknown**, or **not run**. A check passes only when all its required observations pass. A visible failure remains a failure even if some other observations are unknown. Unresolved product choices mean the check is not yet fully defined; deferred delivery is not a pass.

These lists define desired coverage, not demonstrated support. Adding an item creates additional checks; it does not extend previous evidence automatically. The examples and general rules are a draft acceptance specification, not a completed executable test suite or proof of success on every future document.

Optional maintenance references: requirement mapping and execution records and functional requirements. Neither is needed to interpret the behavior described here.
