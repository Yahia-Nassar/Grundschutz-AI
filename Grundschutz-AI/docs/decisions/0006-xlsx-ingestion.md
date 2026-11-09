# ADR-0006: Bounded literal synthetic XLSX ingestion

**Status:** Proposed for human review; implemented for synthetic TASK-006B only.

## Boundary and shared safety mechanics

`ingest_xlsx(path, source_id=..., limits=...)` accepts one explicitly trusted operator-provided synthetic `.xlsx` path. It captures a bounded regular file once and parses only those bytes. It returns frozen/slotted `XlsxExtraction`, `Worksheet` and `CellRecord` dataclasses, retaining original bytes and untrusted literal text. It never follows document paths/relationships, extracts ZIP members to disk, evaluates formulas, invokes inference, writes inventory, records reviews or persists anything. There is no CLI scanning or automatic ingestion-to-extraction adapter.

Reuse the existing DOCX ZIP preflight, capped actual inflation, CRC validation and budgeted XML parser through `ooxml_safety.py`. The move preserves their checks; callers supply separate exact required/allowed part sets and trusted limits. DOCX keeps its existing public types, default limits, parsing rules and `DocxIngestionError` boundary through thin wrappers. Generic low-level error wording now uses OOXML. Existing DOCX tests are unchanged. Keeping one copy of these safety mechanics avoids divergent decompression/parser protections; Word and spreadsheet semantics remain in separate modules.

## Supported XLSX profile: xlsx-literal/v1

Required package parts:

- `[Content_Types].xml`
- `_rels/.rels` with exactly one internal officeDocument relationship to `xl/workbook.xml`
- `xl/workbook.xml` containing only a sheets collection
- `xl/_rels/workbook.xml.rels`
- One to sixteen visible worksheet parts, with canonical names `xl/worksheets/sheetN.xml`, where N is between 1 and the effective `max_worksheets` (default 16). Part numbers do not define sheet order.

An optional `xl/sharedStrings.xml` is the only other supported part. Content types must match ordinary transitional SpreadsheetML workbook, worksheet and optional shared-string parts exactly. Each sheet must have a unique positive `sheetId`, unique case-insensitive name, unique `r:id` and one unique internal worksheet target. Names are preserved exactly and must fit the conservative 31-code-point name profile. Relationship IDs use `rId` followed by a positive integer of at most six digits. Workbook targets use exact relative names such as `worksheets/sheet2.xml`; aliases, absolute targets, traversal, fragments and URL encoding are unsupported. Relationship order, ZIP order, sheet IDs and part numbers never override workbook sheet declaration order. Every package part and workbook relationship must be accounted for.

Worksheets contain only `sheetData`, ascending explicitly numbered rows and ascending explicitly addressed cells. A cell's row must agree with its enclosing row's `r`. Coordinates are canonical uppercase A1 references, with no absolute markers, ranges or leading zeroes; bounds are A1 through XFD1048576. Unordered rows/cells are rejected instead of sorted or renumbered. Sparse coordinates do not allocate intervening rows or cells.

Supported cell representations:

| XML representation | Result |
|---|---|
| `c` with `t="inlineStr"`, one `is` containing one plain `t` | `CellKind.TEXT`, exact parsed text |
| `c` with `t="s"`, one `v` containing a canonical zero-based shared-string index | `CellKind.TEXT`, referenced plain string |
| Empty `c` with an explicit address and no `t` | `CellKind.BLANK`, text `""` |
| Cell absent from XML | No record; `sheet.cell_at(address)` returns `None` |

An empty text string is TEXT, not BLANK. Explicit empty rows remain in `row_indices`. No missing coordinates are synthesized. An empty sheet is supported but a workbook must have at least one sheet.

Shared strings contain only simple `si/t` entries. Rich runs and phonetic content are refused. Every index must resolve; duplicate string-table definitions and unreferenced string-table entries are rejected. Optional `uniqueCount` must equal the table length; optional `count` must equal the actual shared-string reference count across all sheets. No inferred fallback to empty text is permitted.

Text preserves parsed XML characters, including German/Unicode text, explicit tabs/newlines and predefined XML character references. Standard XML 1.0 attribute and line-ending normalization applies when parsing lexical XML; no subsequent trimming, Unicode normalization, number/date conversion or OOXML `_xHHHH_` escape decoding is performed. Boundary whitespace requires `xml:space="preserve"`. OOXML escaped sequences are rejected until their semantics have been implemented and validated explicitly. Sheet names containing such escapes are also rejected.

## Rejected structures

Formula elements are always rejected, including shared/array/data-table formulas and cached results. Numeric, boolean, error, date and cached-formula-string cell types are unsupported. A numeric-looking string explicitly stored as literal text stays text; it is never converted. A formula-looking string in an explicitly literal text cell stays untrusted text and is never evaluated.

Hidden/very-hidden sheets, hidden rows/columns, styles and style references (even index zero), number/date formatting, dimensions, views, merged cells, filters, tables, hyperlinks, defined names, drawings, embedded objects, alternate/extension/dynamic content, comments, macros, external links and data connections are refused. All other parts, elements and attributes outside the allowlist are refused too. This means most ordinary Excel-generated workbooks are unsupported even if they look simple.

ZIP/XML restrictions from ADR-0005 remain: STORED/DEFLATE only, no encryption/ZIP64/spanning/data descriptors/extras/comments, duplicate/aliased names, symlink/directory members, hidden/prefixed/trailing bytes, local/central metadata mismatches, bad sizes or CRCs. XML is UTF-8 with an optional BOM; DTD/entity declarations, CDATA, comments and unsupported processing instructions/encodings are refused. No remote resource is opened. Any failure raises `XlsxIngestionError` without returning partial workbook data.

## Default budgets

Limits are immutable positive integers supplied by trusted code; document content cannot change them.

| Limit | Default |
|---|---:|
| Original XLSX bytes | 2 MiB |
| Aggregate uncompressed ZIP bytes | 8 MiB |
| ZIP entries | 64; current part profile permits at most 21 |
| Per-member expansion ratio | 100:1 |
| XML bytes per part | 2 MiB |
| XML depth / nodes per part | 32 / 20,000 |
| Attributes per node | 16 |
| Expanded element/attribute-name and attribute-value character budget per node | 4,096 |
| Namespace declarations per part | 32; 4,096 characters per declaration |
| XML text characters per part | 2 Mi characters |
| Worksheets | 16 |
| Explicit cells across workbook, including blanks | 10,000 |
| Shared-string definitions | 10,000 |
| Characters in any literal cell/shared string | 16,384 |
| Total shared-string characters | 1,000,000 |
| Flattened extracted characters, including separators and repeated shared-string uses | 1,000,000 |

The XML node budget also bounds explicit empty rows. ZIP member names are bounded to 128 bytes during central-directory preflight. Actual decompression is capped independently of declared sizes and must match declared lengths/CRCs, including when those declarations lie about a truncated prefix. XML budgets apply during parsing. These bounds are not an operating-system sandbox or a claim of comprehensive adversarial hardening.

## Immutable provenance and hash semantics

Every cell carries trusted workbook `source_id`, exact sheet name, one-based sheet ordinal, internal worksheet part, exact cell coordinate, explicit one-based row/column, cell kind, literal text and SHA-256 of `text.encode("utf-8")`. Worksheet records retain `sheet_id`, relationship ID, explicit row indices and ordered cell tuples. Locators describe logical cells, not rendered positions/pages. They are stable for the same structural workbook revision, not for arbitrary later edits.

The extraction artifact retains three distinct hashes:

1. `xlsx_sha256`: SHA-256 of exact original binary XLSX bytes, retained as immutable `original_bytes`.
2. `text_sha256`: SHA-256 of UTF-8 flattened text. `text` joins explicit cell strings with one LF, in workbook-sheet order then validated row/cell order, without a trailing separator. Blank cells add empty strings; missing cells add nothing. Empty sheets add no text.
3. `manifest_sha256`: SHA-256 of `manifest_json.encode("utf-8")`. JSON contains source ID, method/profile version, all effective limits and all ordered worksheet/cell records, including explicit empty rows, kind, coordinates, worksheet identity and per-cell text hashes. Serialization uses `ensure_ascii=False`, `sort_keys=True`, separators `(',', ':')`, and `allow_nan=False`.

Identical flattened text does not imply identical structure. Different coordinates, names, blank kinds or explicit empty rows can have identical text hashes and different manifest hashes. The manifest intentionally excludes raw bytes/the binary hash; merely repackaging identical XML can change binary identity while preserving the manifest. A future source-version binding must retain both. No timestamp or review state is inferred; operational registration time belongs in a separate audit event. Caller-constructed dataclasses are not authenticated ingestion results.

## Future persistence proposal, not implemented

Keep SQLite schema version 1 unchanged. A future separately reviewed source-store/adapter contract must retain exact immutable workbook bytes keyed by binary SHA-256 and trusted source ID/version, plus the ordered extraction manifest, method/policy version, effective limits, exact text/cell hashes, sheet names/order/IDs, relationship/part bindings, row indices, coordinates and blank/text kinds. Register operational timestamps and authenticated origin separately when available.

Reload must verify the binary digest, rerun the compatible bounded parser from the original bytes and compare the regenerated manifest/text/cells/hashes to stored values. A hash or mutable path alone cannot reconstruct the workbook. Missing bytes, mismatches or unsupported policy versions must fail closed; stored extracted text/locators are caches to revalidate, not authority. Preserve historical source revisions and bind later candidate/evidence fingerprints to both raw-document and verified-manifest revisions. A binary-only repackage still represents a distinct registered source revision even if its text manifest is unchanged.

Do not substitute a workbook binary digest for the existing domain `Evidence.source_sha256`, which currently identifies exact UTF-8 source text. There is no adapter from spreadsheet locators to the domain's text-only character locator yet. Future evidence needs sheet/cell identity and exact cell-local quote offsets plus sufficient surrounding workbook context. An isolated positive cell or row must not bypass contradictory/unsupported-context checks. Interpret headers, relationships or inventory facts only through a separately validated candidate/review pathway.

Raw cells and invalid candidates must never become approved facts or appear in generated documents as approved data. Explicit human review remains required, with dependency/revision-bound approval and preserved history. Future exports must handle formula-looking literal strings safely rather than accidentally turning them into spreadsheet commands.

## Remaining limits

The caller must ensure the path is trusted and the data synthetic; ingestion cannot authenticate an author, recognize company confidentiality or prove real-world truth. Hashes are content identifiers, not signatures. A concurrent local attacker, authenticated source registration, access control, retention, parser migration, fuzzing and production security review remain unresolved. No full Excel rendering/compatibility, universal prompt-injection prevention, production readiness or BSI baseline approval is claimed. TASK-006C is not authorized by this decision.
