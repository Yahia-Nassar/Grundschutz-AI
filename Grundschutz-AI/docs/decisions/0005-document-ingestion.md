# ADR-0005: Bounded synthetic DOCX text ingestion

**Status:** Proposed for human review; implemented for synthetic TASK-006A only.

## Decision and boundary

Use Python 3.12 standard-library ZIP, XML and hashing tools in the independent `docx_ingestion` module. `ingest_docx(path, source_id=...)` accepts an explicitly trusted operator-provided path to a synthetic `.docx` file. It reads a bounded regular file once, retains those exact immutable bytes, validates the package, and returns immutable text segments and provenance. It never extracts archive members onto disk or follows relationships, document paths or URLs.

This is a deliberately restrictive text profile, `docx-plain/v1`, not a general Office reader or renderer. Unknown parts/elements/attributes cause `DocxIngestionError`; no partially extracted result is returned. The source ID and limits come from trusted application code, never document instructions. The module neither imports nor calls extraction/Ollama, inventory, review or storage code. Plain instructions inside supported text are returned literally as untrusted data, never executed. No automated approval or document generation is introduced.

## Supported package and text profile

The exact required ZIP parts are `[Content_Types].xml`, `_rels/.rels` and `word/document.xml`. The only optional part is an empty `word/_rels/document.xml.rels`. Content types must declare ordinary transitional WordprocessingML, not a macro-enabled document. The package must have exactly one internal officeDocument relationship targeting `word/document.xml`; all other relationships, including external ones, are refused.

The body supports plain paragraphs and simple rectangular tables, in XML document order. Table cells contain one or more plain paragraphs. A table may have empty `tblPr` and a matching positive-width `tblGrid`. Runs contain only text, tabs, carriage-return breaks or text-wrapping line breaks. Empty paragraphs are retained. Text is not trimmed, case-folded or Unicode-normalized. Boundary whitespace requires explicit `xml:space="preserve"`. An empty final `sectPr` is allowed; layout properties are not supported.

The following are rejected rather than silently omitted:

- Tracked insertions/deletions/moves, comments, fields, hyperlinks, alternate/embedded content, drawings, images, objects, content controls and other unknown elements.
- Styles, run/paragraph properties (including hidden/struck text), numbering, headers, footers, footnotes, endnotes and document properties/settings/theme parts. Most ordinary Word-produced files therefore fail this profile even if they appear simple.
- Merged, nested or ragged tables, cell properties, page/column breaks, nonempty section properties and unsupported namespaces or attributes on parsed elements.
- Macros, encryption, directory/symlink members, duplicate or aliased names, extra package parts, noncanonical local/central ZIP metadata, ZIP64/spanning, comments, data descriptors, extra fields, prefixed/trailing/hidden bytes and compression other than STORED or DEFLATE.
- XML encodings other than UTF-8 (optional BOM), DTD/entity declarations, CDATA, XML comments and processing instructions other than a supported XML declaration. Predefined XML character references remain supported.

No PDF/XLSX ingestion, Office compatibility claim or page-number inference is made. The reader preserves logical text and structure within this profile; it does not reproduce visual layout or prove the truth of text.

## Resource limits and validation

Default limits are trusted, immutable `DocxLimits`; every value must be a positive integer. The chosen profile is recorded with each result.

| Limit | Default |
|---|---:|
| Original file | 2 MiB |
| Total uncompressed ZIP bytes | 8 MiB |
| ZIP entries | 16 (the allowed parts currently permit at most 4) |
| Per-member decompression ratio | 100:1 |
| XML bytes per part | 2 MiB |
| XML depth / nodes per part | 32 / 20,000 |
| Attributes per node | 16 |
| Expanded element/attribute-name and attribute-value characters per node | 4,096 |
| Namespace declarations per part | 32; each declaration also has a 4,096-character budget |
| XML text characters per part | 2 Mi characters |
| Extracted segments | 4,096 |
| Characters per segment | 16,384 |
| Flattened text characters, including separators | 1,000,000 |
| Rows / columns per table | 1,000 / 128 |

ZIP central records are preflighted before `ZipFile` allocates its member list. Local headers must agree with central records and member data must cover the archive contiguously. Actual decompression is capped independently of declared sizes; size and CRC are then checked. This avoids relying on a possibly forged member length to bound inflation or to accept a truncated prefix. Aggregate declared sizes are checked before decompression and each accepted actual size must match its declaration. XML depth/nodes/attributes/namespaces/text budgets are enforced during parsing, not after building an unrestricted tree. Source text is never logged by the reader.

These are bounded in-process safeguards, not a sandbox, fuzzing campaign or production security certification. Trusted callers may choose other limits deliberately; document content cannot change them.

## Locators and hashes

Each `TextSegment` is a single body paragraph or a single paragraph within a table cell. Every locator has `part="word/document.xml"`. Indices are one-based:

- `body_index`: body child position, distinguishing paragraphs and tables in their shared order.
- Body paragraph `paragraph_index`: the ordinal among body paragraphs only; table/row/cell indices are null.
- Cell paragraph `paragraph_index`: the ordinal within that cell; `table_index`, `row_index` and `cell_index` identify the table, row and cell. Table indices count body tables only. Cells are visited row first, then column, then paragraph.

`char_start` and `char_end` are zero-based, half-open Python Unicode code-point offsets **within the segment**, not UTF-8 byte offsets, grapheme positions or offsets into the whole document. A full segment covers `[0, len(text))`; `segment.span(start, end)` produces a checked substring locator. Empty paragraphs cover `[0, 0)`. Locators are stable for the same structural document revision, not across arbitrary edits. There are no invented page numbers.

`DocxExtraction.text` joins all segment strings using one literal LF (`\n`), with no trailing separator. Tabs and text-wrapping breaks inside a paragraph become `\t` and `\n`. Empty segments remain in the sequence. Flattened text is a convenience view, not a replacement for the ordered segment manifest: different structures can flatten to the same string.

- `docx_sha256`: SHA-256 of the exact captured binary DOCX bytes, retained as `original_bytes`.
- `text_sha256`: SHA-256 of `text.encode("utf-8")` with no BOM or additional normalization.
- Each segment also has its own UTF-8 `text_sha256`.

Results include the trusted source ID, method version and limits profile. They deliberately contain no review state, approvals or current-time fields; repeated ingestion of identical bytes/configuration yields equal immutable results. A future operational ingest timestamp belongs in a separate audit event. Different ZIP packaging can change the binary hash without changing the text hash. Hashes detect content changes but do not authenticate an author or prove real-world truth. The result dataclasses describe artifacts; arbitrary caller-constructed instances are not authenticated evidence.

## Proposed future persistence contract (not implemented)

Keep SQLite schema version 1 and `InventoryStore` unchanged in this task. A separately reviewed migration/adapter will need to:

1. Retain exact immutable raw DOCX bytes in a trustworthy local source store, keyed by their binary SHA-256 and bound to a trusted source ID/version. An unverified path or a hash without the original bytes is insufficient for reproducible reload. Record registration/audit time and authenticated origin separately when available.
2. Retain an ordered extraction manifest binding the binary digest, parser/profile version, effective limits, UTF-8 text digest, segment texts/digests and full structural locators. A manifest must distinguish segment order/structure even when flattened text is identical.
3. On reload, verify the raw-byte digest and rerun the compatible bounded parser from the original bytes. Compare regenerated text, segment hashes, order and locators to the manifest; fail closed on missing bytes, mismatches or unsupported policy versions. Stored derived text/locators are caches to verify, not independent authority.
4. Bind later evidence to the document source/version and binary digest, segment identity and digest, exact quote and segment-local span, extraction method and policy version. Preserve the containing document context so selecting an isolated positive sentence cannot bypass existing contradictory/unparsed-source checks. Source segmentation and candidate context need explicit review before an ingestion-to-inventory adapter exists.
5. Keep binary-document hashes distinct from the existing domain `Evidence.source_sha256`, which currently hashes exact UTF-8 source text. Do not substitute the DOCX digest for a text digest, fabricate a page locator, or pass these new locators into the existing character-only locator without a reviewed mapping. Revisions/fingerprints must eventually bind both the raw-document revision and the verified extraction manifest.
6. Keep all extracted text and raw invalid candidates untrusted. No ingestion artifact is an approved inventory fact. Future adapters must preserve validation/review gates, dependency-bound explicit human approval and history. Document generation must use only the current approved inventory view, never diagnostic candidates or raw ingestion values as approved facts.

Authentication, access control, confidentiality/retention policy, tamper-resistant audit, parser-policy migration and adversarial fuzzing remain future work. A trusted path is a caller responsibility, not a document authenticity guarantee or a complete defense against a concurrent local attacker. No company documents, BSI baseline changes or TASK-006B work are authorized by this decision.
