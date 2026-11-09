# ADR-0007: Synthetic PDF feasibility and security contract

**Status:** Implemented for TASK-006C.1 experimental structural diagnostics under the user's explicit C.1 instruction; results await human review. Rendering, approved-inventory use, dependencies and persistence changes remain outside the authorized implementation.

TASK-006C.1 update: the user's explicit C.1 instruction authorizes implementation of this experimental structural profile. The C.0 discussion below remains historical; the finalized grammar and actual C.1 findings at the end supersede its pending implementation details. Visual verification and approval remain unavailable and unauthorized.

## Evidence and choice

Local inspection on 2026-11-09 found Python 3.12.6, 64-bit, at `C:/Python312/python.exe`. In both the normal environment (user site enabled) and `-I` isolated mode, module discovery found none of `pypdf`, `PyPDF2`, `pymupdf`, `fitz`, `pdfminer`, `pdfplumber`, `pikepdf`, `pypdfium2`, `reportlab`, `fpdf`, `borb`, `pdfrw` or `ghostscript`. Distribution metadata contained no names matching pdf, mupdf, reportlab, ghostscript or borb. The PATH check found none of `pdftotext`, `pdfinfo`, `pdftoppm`, `pdftocairo`, `mutool`, `qpdf`, `gswin64c`, `gswin32c`, `gs` or `verapdf`. No package was imported to parse a document, and no document or PDF tool was executed. This establishes absence from the checked environments/PATH, not absence from every directory or other Python environment on the machine.

| Approach | Feasibility and complexity | Dependency implications and limitations |
|---|---|---|
| Exact synthetic byte/grammar profile, standard library | Recommended for TASK-006C.1 as a small experimental validator/text reader. Moderate implementation effort: exact object graph, cross-reference offsets, lengths, page ordering, geometry and negative tests are still necessary. | No new dependency. Intentionally rejects practically all ordinary PDFs; ASCII-only and no renderer. It is not a general PDF parser or sanitizer. |
| Existing local parsing/rendering library or CLI | No suitable package/tool was discovered. No local version, license, API behavior, output quality or rendering independence can be validated. | Not currently usable. Do not substitute a browser/viewer, another Python interpreter, network service or opportunistic PATH executable. |
| Future approved offline dependency | A maintained parser plus a separate renderer can eventually support a wider profile. A library does not remove the need for feature rejection, output/context validation, resource isolation or review. | Requires a separately approved exact-version/artifact lock, verified license texts/notices, Windows/Python compatibility, transitive/native dependency inventory and security review. Currently unresolved; no dependency is approved or available here. |

For a concrete **comparison-only historical pin**, consider `pypdf==5.1.0`, with an **expected BSD-3-Clause license**, as a pure-Python parsing category rather than a renderer. The numeric pin and expected license are prior-knowledge candidates, **not locally verified findings, a current-version/security recommendation or an approved installation**. No wheel, license file, version-specific behavior or advisory record for it was available to this inspection. Do not turn this example into a requirements entry. A future dependency decision must confirm or replace this historical pin using an approved offline artifact and document its actual bundled licensing; freshness and security cannot be established by this no-network task.

An acceptable future lock must contain an exact numeric package version, SHA-256 of every approved wheel/binary, Python/Windows ABI, all transitive/native component versions and hashes, SPDX identifiers supported by retained license texts, attribution/distribution obligations, offline security-review evidence and explicit approval. Wildcards, unpinned latest versions, a remembered license name or an unverified historical example do not satisfy that gate. A renderer needs its own independently reviewed version/license/artifact lock and capability restrictions. Neither component may auto-fetch fonts, models, updates or other resources. There is no legal or security clearance for an unavailable package in this decision.

**Recommendation:** limit TASK-006C.1 to a standard-library reader for the proposed `pdf-synthetic-ascii/v1` profile below, together with temporary synthetic fixtures and fail-closed tests. Do not expand the grammar to make ordinary PDFs pass. If the implementation needs general PDF recovery, font interpretation or layout inference, stop and request a separately scoped dependency/profile decision. Structural extraction can be tested without a renderer; visual correspondence must remain explicitly unverified until an independent rendering check is available. No claim of visually verified PDF evidence is permitted in the meantime.

## Proposed supported profile: pdf-synthetic-ascii/v1

This is a canonical **test-file language expressed as valid simple PDF**, not an allowlist discovered by scanning arbitrary PDF bytes for friendly keywords. A future fixture builder and parser must specify the same canonical lexical grammar, while tests use independently stated expected text/locators and deliberate byte mutations. No fixture or parser is created in TASK-006C.0.

### Whole-file and object structure

1. One trusted explicit path to a synthetic regular `.pdf` file; capture its bounded original bytes once. The path and source ID are trusted application input. Never reopen a mutable path for later verification instead of retaining those bytes.
2. Exact PDF 1.4 header `%PDF-1.4` with LF. One revision only, LF-only canonical syntax, one classic cross-reference table, one trailer, one `startxref` and one final `%%EOF` with LF. No prefixes, suffixes, unrelated comments, hidden bytes, additional EOF sections or repair/recovery behavior.
3. Exact object graph: object `1 0` is the catalog, `2 0` a flat Pages node, `3 0` the sole font. Page ordinal i has Page object `2*i+2 0` and content-stream object `2*i+3 0`. Exactly `3 + 2*page_count` objects occur once each in ascending physical object order; no other or unreachable objects. The flat Kids array explicitly references those pages in that order, and Count must match. Page parents refer to `2 0`.
4. Catalog contains only Type and Pages. Pages contains only Type, Kids and Count. Each Page contains only Type, Parent, fixed MediaBox `[0 0 595 842]`, its explicit Resources/Font/F1 reference to `3 0`, and one Contents reference. No resource/box inheritance, nested page trees, arrays of streams, crop boxes, rotation, UserUnit, page labels or extra dictionaries.
5. The only font dictionary is Type Font, Subtype Type1, BaseFont Courier, Encoding WinAnsiEncoding. No custom encoding/Differences, font descriptors, embedded fonts, Type3 fonts, CMaps, ToUnicode, ActualText, marked content or fallback character decoding. Only the printable ASCII subset of this explicitly fixed encoding is accepted; no assumption is made about arbitrary fonts or missing mappings.
6. Each content stream has only a direct canonical integer Length. The exact payload length and delimiters must match. No filters, compressed/object streams, indirect lengths or searching for endstream as a recovery strategy. Raw stream bytes are bounded before inspection; there is no PDF decompression pathway.
7. The classic xref has one subsection from object 0 through the last object, the canonical free entry for object 0, fixed-width entries and exact byte offsets to every actual object header. All used generations are zero. Validate Size, Root, startxref, offsets, unique entries, object boundaries and full byte coverage. Trailer keys are only Size and Root. No Prev, XRefStm, Encrypt, Info, ID, hybrid/xref streams or incremental updates.
8. C.1 must define the exact whitespace, dictionary-key order, number and delimiter spelling for these templates before coding. Variants are unsupported, not opportunities for tolerant parsing. All numeric/string tokens and object counts are bounded. A monotonic bounded cursor or equivalent full-consumption grammar is required; regex keyword extraction, searching only referenced objects or accepting a valid prefix is insufficient. Names/keys/operators outside the schema fail, even if believed harmless.

### Text, content order and visibility restrictions

Each page has exactly one text object. Its allowed operator sequence is `BT`, `/F1 12 Tf`, then zero to 38 pairs of an exact text matrix and a hex-string `Tj`, then `ET`. For line ordinal j, the matrix must be `1 0 0 1 72 y Tm` with integer `y = 770 - 18*(j-1)`. Hex strings contain an even number of uppercase hex digits representing zero to 60 bytes, each in `0x20..0x7E`; each byte maps directly to the corresponding ASCII Unicode code point. Empty hex strings represent explicit blank lines. There is no trimming, inferred whitespace, Unicode normalization, replacement character or transliteration. Genuine German umlauts/ß or other non-ASCII text are **unsupported**, not converted to ae/ss or guessed from glyphs.

No operators other than the exact sequence above are supported: no TJ arrays/spacing, relative text positioning, alternate fonts/sizes, text transforms, rendering modes, color/alpha changes, graphics state, clipping, paths, images, XObjects, optional layers or marked content. The baseline progression gives one explicit top-to-bottom line order and avoids intentional overprinting; fixed Courier advance and maximum line length place nominal text well inside the page. This restriction is not proof of real glyph bounds or renderer behavior. Font substitution, glyph appearance and actual visual correspondence still require the independent check below.

For zero text lines, the page is an explicit supported blank page, not a discovered scan. A PDF containing an image, vectorized lettering or unknown content fails the profile instead of returning an apparently empty supported page. No OCR or scan classification is implemented. A later richer profile would need explicit image-only/unreadable-page findings and could not silently treat them as evidence of missing facts.

## Feature handling and failure contract

| Condition | Required disposition |
|---|---|
| Multiple canonical pages | Preserve every page in validated Kids order; keep blank pages. Do not sort by object ID, a printed page label or text coordinates in a general document. |
| Multiple columns, reordered/overlapping text, noncanonical matrices, clipped/invisible/transparent/rotated text | Reject the whole input as unsupported. No heuristic reordering or hidden-text filtering. |
| Missing/unknown encoding, custom/ambiguous glyph mappings, unsupported Unicode, ActualText/ToUnicode variations | Reject. The sole exception to requiring a Unicode map is the precisely defined ASCII/base-font/encoding combination above. Never guess or emit replacement characters. |
| Scans/images/vector letters | Reject the unsupported structure; require human clarification outside the reader. No OCR, empty-page substitution or omission of the affected page. |
| Forms/XFA, annotations/widgets, appearance streams, attachments/embedded files, portfolio objects, multimedia or 3D | Reject all such structures; never flatten, execute or silently discard them. |
| JavaScript/actions, OpenAction/AA, Launch/URI/remote GoTo/file specifications, external resources | Reject actual unsupported syntax/objects. Never follow a URL/path or run an action. The same words in an allowed literal hex text line are untrusted text, not instructions or a keyword-blacklist match. |
| Encryption/passwords, signatures/incremental revisions, duplicate keys/objects, cycles, bad xref/counts/lengths or trailing bytes | Reject, no passwords, repair, latest-revision fallback or partial extraction. Signature verification is not implemented or inferred. |
| Unknown feature or resource budget exceeded | Reject with a bounded reason code; return no partially trusted page/text collection. |
| Accepted profile but renderer absent, visual check inconclusive or visual mismatch | Preserve explicitly untrusted diagnostics/verification outcome only. No visually verified-evidence claim; any attempted downstream use requires clarification and separate human review. |

Proposed parse error categories are invalid input, unsupported profile, resource limit and timeout; none is a new domain review state. An accepted extraction artifact also has no approved state. Visual findings should be separate audit records (`not_run`, `matched`, `mismatch`, `inconclusive`) bound to its exact source/manifest and renderer configuration. These are verification outcomes, not new `ReviewState` values. An outside review workflow may record existing `needs_clarification`; the reader must not manufacture a reviewer or ReviewRecord. A matched rendering check alone never grants approval.

On any invalid/unsupported page, fail the entire extraction, including when earlier pages parsed correctly. Error messages/logs must not contain source text. Any deliberately retained raw candidate/partial diagnostic data is clearly untrusted and excluded from approved-data views and document generation. Human clarification cannot override malformed-source rejection into a verified extraction; a new conforming source or separately approved profile and revalidation is required.

## Proposed limits for C.1

These are design values, not measured performance or implemented enforcement. Effective caps must be trusted, immutable and recorded with the result; document input cannot relax them.

| Limit | Initial proposal |
|---|---:|
| Original bytes | 1 MiB |
| Pages | 16 |
| Indirect objects | Exactly `3 + 2*pages`, at most 35 |
| Xref entries | Object count plus the single free entry |
| Content stream bytes | 16 KiB per page, no compression or filters |
| Grammar nesting / non-stream token bytes | At most 8 / 128 |
| Text lines per page / characters per line | 38 / 60 ASCII code points |
| Page text characters including LF separators | 2,317 |
| Document text characters including page separators | 65,536 (also constrained by page/line caps) |
| Proposed parser worker wall time | 5 seconds per file; parent-enforced, validate on Windows in C.1 |
| Proposed worker result size | 256 KiB; parent must cap reads and kill/reject on excess |

The future parser must make bounded progress and reject before allocations based on untrusted counts/lengths. No generic recursive object resolution, decompression, image decoding or embedded-program execution. A parent process should send captured bounded bytes to a fixed trusted Python worker and enforce deadline/output bounds; threads alone cannot terminate a stuck parse reliably. Worker executable/module and arguments must come from trusted configuration, with no shell and no document-controlled command arguments. This is containment against parser failure, not a configured OS security sandbox. Do not claim a portable hard RSS limit from Python standard-library bounds alone; peak memory and actual deadline behavior need future measurement/tests. No security settings are changed by this proposal. Existing OOXML ZIP/XML code is not a PDF parser and is not reused for PDF syntax.

## Source, locator and reconstruction contract

The future result should be typed, frozen records, independent of Ollama/domain/storage. A trusted `source_id` plus exact original bytes and `pdf_sha256 = SHA256(original_bytes)` identify the captured document revision; the mutable path is operational metadata, never the content identity. Keep the raw bytes in memory for this bounded prototype and, eventually, an authenticated local immutable source store. A hash without those bytes cannot reconstruct or visually inspect the PDF.

For every page retain:

- `page_index`: explicit **one-based** ordinal from the completely validated page tree, including blank pages; Page/content object number and generation are separate structural references.
- `text`: exactly the decoded line strings joined with one LF, no trailing LF; zero lines gives `""`. An explicit blank line remains in the line manifest even when its flattened text is empty.
- `text_sha256`: SHA-256 of page text encoded UTF-8, without BOM. A line record has its own exact text, ordinal and zero-based half-open character span in **that page text**, plus the verified content-object identity and byte span of its hex operand in the captured PDF.
- Quote locators use `(source_id, pdf_sha256, page_index, char_start, char_end)` with exact quote equality to `page.text[start:end]`. Offsets are Python Unicode code-point offsets, not PDF bytes, pixels, glyph indices or whole-document offsets. Quoted fact spans must be nonempty. Checked line/character spans must never cross page boundaries.
- Nominal line baselines, if retained, are in PDF user-space points with a stated origin, not invented measured glyph boxes. Optional future raster boxes need a recorded renderer/scale/rotation/origin and separate verification. Printed page labels and page-like strings inside content never replace page_index.

Keep page order, line content order, PDF physical object order and visual positions as separate concepts, even where this narrow grammar deliberately makes them consistent. Sorting by geometry, inferring pages from form feeds, or borrowing DOCX page assumptions is forbidden. Page indices are stable for a given original PDF revision; inserting/reordering pages creates a different source revision.

The full-document text convenience view joins page strings with one form feed (`\f`), with no trailing separator. Source text cannot contain form feeds in this ASCII profile. Nevertheless, flattened text alone is insufficient: explicit blank lines/pages, object mappings and boundaries must remain in an ordered manifest. Retain both the document UTF-8 `text_sha256` and page hashes.

The proposed canonical manifest contains source ID, **original pdf_sha256**, extraction method `pdf-synthetic-ascii/v1`, exact parser implementation/version (future module/release or source-artifact digest), effective limits, ordered page/object references, page text/hashes and complete ordered line/quote mapping data. Use UTF-8 canonical JSON with sorted keys, compact separators, `ensure_ascii=False`, `allow_nan=False`, no floats for this integer geometry and no current timestamps; `manifest_sha256` hashes those exact JSON bytes. This PDF provenance manifest deliberately binds binary identity; unlike the XLSX structure-only manifest, a binary-only change also changes this manifest. The binary digest, text digest and manifest digest remain distinct values with distinct purposes.

Operational registration/review time belongs in a separate timezone-aware audit event. A future rendering observation is a separate manifest-bound record with tool/configuration/image digests, not an automatically approved field in the deterministic extraction. Hashes and re-extraction identify/verify bytes and derivations, not author identity, physical truth or human authorization.

Future reload must retrieve original bytes for the exact source revision, check their binary digest, rerun the compatible profile/parser/limits, and compare regenerated page text, hashes, offsets, byte mappings and canonical manifest. Verify that each quoted span and its raw-stream operand mapping reconstruct the same text. Missing bytes, incompatible policy/version or any mismatch blocks use; never fall back to cached approved text. Preserve all historical source registrations and approval fingerprints, including a return to earlier bytes as a new registration.

**No SQLite change:** schema version 1 currently retains exact UTF-8 source BLOBs and domain character locators, not raw PDF/structural manifests. Do not put PDF binary bytes into that text contract, replace `Evidence.source_sha256` with a binary digest, or map page-local offsets into the domain locator without a separately reviewed adapter/migration. Future candidates must retain enough whole-document/page context to expose conflicting or unparsed assertions. Extracted text is always untrusted and never automatically invokes Ollama. Only validated proposals can enter a separately validated domain pathway; `needs_clarification`/`rejected` fields and raw diagnostics cannot enter approved inventory. Existing explicit human review, exact revision/dependency fingerprints and preserved histories remain mandatory. No new approval pathway is proposed.

## Independent visual verification

No renderer is available in the inspected environment, so this check was **not performed**. Do not mark it passed or infer equivalence from text/hash tests.

A future independently implemented, approved offline renderer (a different implementation from the extraction validator) should consume the **same captured PDF bytes**, in a separate bounded process. Pin its version, executable/artifact hash, bundled font assets/fallback policy and render parameters. No actions, external fonts/resources, network fetches or shells. If those restrictions cannot be established, do not render it as a trusted check. Parser validation precedes rendering, but renderer bugs remain a separate threat.

Render each page in isolation at fixed settings, for example 144 DPI, zero rotation, RGB on white; record actual dimensions, coordinate transformation, image digest and tool diagnostics. Suggested future limits: 3 million pixels per page, one page in memory at a time and a parent-enforced 10-second deadline per page. Limits need benchmarking; do not claim enforcement now. Missing/substituted fonts, unexpected page counts, truncated/blank output or warnings make the check inconclusive.

Without OCR, a human compares all independent page rasters with the page-local strings/ordered line baselines, looking for absent/extra glyphs, hidden extraction-only assertions, clipping, overprinting and order changes. For synthetic regressions, independently specified expected strings and human-reviewed golden rasters under the pinned renderer can flag changes; creating expected output solely through the parser/fixture builder would hide shared errors. Exact pixel hashes are only comparable under the same pinned renderer/fonts/settings, and a pixel difference is a review signal rather than automatic proof of a semantic difference. A raster hash alone does not establish text equivalence. Rendering can reveal discrepancies but cannot prove correct reading order, semantic truth or universal absence of hidden content.

## Focused C.1 synthetic test matrix

All fixtures must be explicitly fictitious, constructed in temporary directories outside Git using only authorized tools. This matrix is proposed, **not executed PDF tests**.

| Test family | Expected evidence or disposition |
|---|---|
| Single-page inventory sentence; two/three pages; last page, blank page and explicit blank lines | Exact ASCII text, Kids page order, one-based page indices, no omissions; blank structures retained in manifest. |
| Multiple canonical lines, spaces, empty lines and ASCII punctuation such as parentheses/backslashes represented in hex | Exact decoding, LF separators and page-local spans; no trim, guessed whitespace or escape interpretation. |
| Page-local quote on pages 1 and 2; last character, empty/negative/out-of-range/cross-page spans | Exact quote equality for valid nonempty spans; reject invalid locators. Verify object/raw operand spans too. |
| Same text with different page/line partition or different original bytes | Text hash alone never establishes provenance; page/manifest/binary hashes reflect their defined changes. Repeat extraction of identical bytes/configuration equals exactly. |
| Printed content saying page 99; altered Kids/counts/parent links | Printed label remains literal text; actual page index stays structural. Noncanonical/reordered/cyclic/dangling Kids structure is rejected, never sorted/repaired. |
| Non-ASCII bytes, unknown font/encoding, custom CMap/Differences/ToUnicode/ActualText | Reject with no guessed character, transliteration or replacement output. |
| Two columns, wrong line matrix/order, zero font size, alternate font, Tr=3, white/transparent text, clipping, overlays, rotation | Reject every unsupported layout/graphics change, including a valid earlier page followed by an invalid later page; no partial result. |
| Image-only scan, image plus text, vectorized glyphs, layers/XObjects or compressed content | Unsupported failure; no OCR or empty-page success. Canonical truly blank page remains distinguishable. |
| Forms/XFA/widgets/annotations/appearances, attachments, JavaScript/OpenAction/AA/URI/Launch/external references | Reject actual unsupported structure without invocation/resource access. The same words and malicious instructions in valid literal text remain inert untrusted data. |
| Encryption, signature/incremental append, xref/object streams, Prev/hybrid revisions, garbage prefix/suffix | Reject completely; no passwords, repair or last-revision fallback. |
| Duplicate objects/keys, false stream length containing delimiter-like bytes, bad xref/startxref/Size/generations, truncation/unknown object | Validate full byte coverage and exact grammar; no prefix acceptance, object scanning or alternate interpretation. |
| File/page/object/stream/token/nesting/line/character/output bounds and worker deadline | Boundary-size positives and one-over negatives; fail before unbounded allocation, kill timed-out/over-output worker and return no artifact. Compression bombs fail at unsupported filter syntax, not during inflation. |
| Missing/corrupt raw bytes or manifest, stale parser policy/source registration | Future verification/replay must block use; no cached approval fallback. C.1 can test in-memory verification without persistence. |
| Side effects and immutability | Patch inference, HTTP/process launches other than the trusted worker, inventory/review/storage writes and assert none from document text. Frozen typed output; no approved state, no text logs or source files left in Git/temp. |
| Independent raster check, once a renderer is approved | Known visible fixtures match human-reviewed expectations; mismatches/inconclusive/not-run remain explicit. Unavailable renderer is an unresolved check, never a fake pass. No OCR. |

Before C.1 structural-reader acceptance, finalize the canonical fixture spelling, test that complete-byte coverage rejects hidden content and record measured parser resource behavior on this Windows/Python environment. Before claiming visually verified extraction, demonstrate that valid fixtures open and correspond to their expected text in an approved independent renderer. Structural-reader tests and independent visual verification must be reported separately. The former can succeed while the latter remains unavailable; an unavailable visual gate remains unresolved.

## Threat model and unresolved gates

Assume malicious synthetic bytes, fraudulent text/instructions, corrupt xrefs/counts, hidden/contradictory content and attempts to exhaust resources. Trust only the operator-supplied path/configuration, approved runtime/code, and original bytes after capture as a versioned input, not as factual truth. Local filesystem races, a compromised interpreter/tool, source authenticity, protected storage, authenticated reviewers, full PDF conformance, Unicode/rich-layout handling, independent-renderer licensing/pinning and adversarial fuzzing remain unresolved.

C.0 completes design and local feasibility evidence only. C.1 must be separately requested and confined to this profile or a reviewed amendment. Wider PDF acceptance and visually verified-evidence claims remain blocked by the missing approved dependency/renderer artifacts, licenses and compatibility/security/rendering validation. No installations, network access, security-setting changes, company documents, OCR, automatic commits or BSI baseline changes follow from this document.

## Finalized C.1 canonical byte grammar (recorded before parser implementation)

All templates below are ASCII bytes. Every displayed line ends in exactly one LF byte (`0A`), including the final EOF line. Spaces are single ASCII spaces exactly as shown. There are no tabs, CRs, blank separator lines or other bytes outside text hex operands. `{...}` denotes a validated substitution, never literal braces. Variable decimal integers have no sign or leading zeroes; the xref entries are the explicit fixed-width exception. Dictionary key order is exact. No dictionary extensions or alternate spellings are accepted.

File prefix, for page count P from 1 through 16:

```text
%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Count {P} /Kids [{KIDS}] >>
endobj
3 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>
endobj
```

KIDS is `4 0 R` for one page, `4 0 R 6 0 R` for two, and so on, with a single space between references, no initial/trailing space. For each page i in Kids order, append the following two objects. A is `2*i+2`, C is `2*i+3`. L is the exact number of payload bytes from `BT` through the LF after `ET`, excluding the LF after `stream` and excluding `endstream`:

```text
{A} 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {C} 0 R >>
endobj
{C} 0 obj
<< /Length {L} >>
stream
BT
/F1 12 Tf
{ZERO_OR_MORE_LINE_PAIRS}ET
endstream
endobj
```

ZERO_OR_MORE_LINE_PAIRS is zero to 38 repetitions of exactly:

```text
1 0 0 1 72 {770-18*(j-1)} Tm
<{HEX}> Tj
```

j is the one-based line ordinal. HEX is zero to 120 uppercase hexadecimal digits, an even count, decoding only printable ASCII bytes `20..7E`. Hex-operand byte spans include both angle brackets and exclude the following space. A blank page has no pairs; a blank line has `<> Tj`. The payload already ends with LF; no extra LF is inserted before `endstream`.

After all objects append exactly:

```text
xref
0 {N+1}
{FREE_ENTRY}{ENTRY_1}...{ENTRY_N}trailer
<< /Size {N+1} /Root 1 0 R >>
startxref
{X}
%%EOF
```

N is `3+2*P`; X is the zero-based byte offset of the `x` in `xref`. FREE_ENTRY is exactly the 20 bytes `b"0000000000 65535 f \n"`, including its trailing space and LF. Each ENTRY_k is its own 20-byte line: the exact ten-digit zero-padded original byte offset of `{k} 0 obj`, followed by ` 00000 n ` and LF. ENTRY placeholders are explanatory concatenation, not extra syntax. Object offsets point to the first decimal digit, not an earlier separator. All generations except the free xref entry are zero. Exact templates account for every original byte; extra/repeated/unused objects, duplicate keys, false lengths, offsets, generations, appended revisions and whitespace variants are rejected without recovery.

The profile's maximum dictionary/array nesting is fixed at three and its fixed-name token spellings are bounded. The effective depth/token budgets can only tighten the ADR caps; neither introduces a generic recursive grammar. Hex operands, numeric tokens, stream sizes and all record counts have separate bounds. Parser implementation/version is `grundschutz_ai.pdf_ingestion/1.0.0` initially; semantic changes require a new implementation version and revalidation.

Parent/worker protocol is private version 1: a four-byte big-endian JSON-header length (at most 16 KiB), an exact-key UTF-8 header containing protocol/source_id/effective limits/raw_size, then precisely raw_size captured PDF bytes and EOF. Source IDs are nonempty trusted strings of at most 256 UTF-8 bytes. Limits may tighten but never exceed this profile's caps. Worker stdout is a single exact-key JSON success envelope with the full deterministic manifest and manifest hash, or a bounded error-code envelope. No pickle, arbitrary class loading, document-controlled arguments or shell. The parent rejects unknown/duplicate keys, bad types, inconsistent source/limits/hashes, bad line/raw-byte mappings, invalid/truncated output and unsuccessful exits. Visual state is always `not_performed`, diagnostic-only is always true.

The parent starts the five-second deadline before launch, writes captured bytes and drains stdout concurrently using bounded pipe operations, and retains no more than the result cap plus one overflow-detection byte. Timeout/overflow triggers kill and bounded reap/join cleanup; cleanup may take up to an additional bounded interval and is not counted as successful parsing. A cleanup failure is an error, never accepted output. Stderr is discarded and source text is not logged. This is a trusted local subprocess boundary, not an OS sandbox or hard RSS guarantee. Actual Windows lifecycle tests and results are recorded in TASK-006C1-RESULTS.md.

## Actual C.1 implementation findings

The public API is `grundschutz_ai.pdf_ingestion.ingest_pdf(path, source_id=..., limits=...)`. `_parse_canonical` is the private worker core, not a public in-process ingestion alternative. `PdfLimits` defaults match the caps above and permits only positive integer tightening, never relaxation. `ObjectRef`, `PdfLine`, `PdfPage`, `PdfQuote` and `PdfExtraction` are frozen/slotted typed records. Each extraction has fixed `diagnostic_only=True` and `visual_verification="not_performed"`; no approved/verified status is created. `quote(page_index, start, end)` and `verify_quote(quote)` provide exact nonempty source-revision/page-local substring matching only, not visual or factual verification.

The parent executes `[sys.executable, '-I', '-S', '-u', absolute_trusted_pdf_worker_script]` with no shell, stdin/stdout pipes, discarded stderr, closed unrelated descriptors and `CREATE_NO_WINDOW` on Windows. The isolated worker adds only its trusted application root to import the private parser. Python site initialization, user site and PYTHONPATH are excluded. Captured bytes/configuration pass solely through the bounded stdin frame. The trusted worker script never creates descendants or follows source instructions.

Two pipe threads perform partial-write-aware input transfer and bounded stdout reads; they do not parse PDFs. The main parent supervises the process with a monotonic deadline, requires a successful exit plus complete input/output before decoding, and rejects rather than accepting an early valid-looking prefix. It caps retained stdout at 262,145 bytes (256 KiB plus one overflow sentinel); it does not use unbounded `communicate`/capture-output buffering. Timeout/overflow/startup failure enters the same direct-process kill/reap and thread/pipe cleanup path. Cleanup has a separate shared one-second deadline. Failure to reap or join is `worker_cleanup_failed`, never a successful artifact. The five-second budget covers launch/IPC and result checking after file capture; blocking OS process creation/termination and file I/O are not hard real-time guarantees. No process-group sandbox, hard RSS cap or protection against a compromised runtime/local code is claimed.

The parent strictly decodes exact-key version-1 JSON, rejecting duplicate keys, nonfinite numbers, truncated/malformed/unexpected results, bad types (including bool/int substitutions), unsuccessful exits, source/limit/version/hash mismatches and fabricated line/raw-operand mappings. It regenerates the canonical manifest and hashes from captured bytes and typed records. The trusted worker remains responsible for complete original-file grammar/graph validation; the parent does not rerun the full PDF parser outside its worker deadline. Dataclass construction is not an independent source-authentication boundary or an approval pathway.

Actual Windows tests passed: **279 offline tests (235 existing + 44 PDF), zero failures/errors**, including real stalled/blocked-input/output-flood workers, process/thread cleanup and a literal independently fixed-offset PDF. A separate observed timeout returned at 5.000 seconds; an output flood was rejected in 0.047 seconds, with worker reaped and pipes closed in both cases. A maximum 16-page/608-line fixture used 91,780 original bytes, 37,087 text characters and a 140,788-byte worker result; observed ingestion was 0.204 seconds. These are individual observations, not latency/memory guarantees. Peak RSS was not measured. Complete results, hashes, test commands and remaining limitations are in `docs/tasks/TASK-006C1-RESULTS.md`. Independent rendering was not performed; no wider PDF acceptance, PDF-to-Evidence/Inventory adapter, SQLite change, approved facts or TASK-007 work is introduced.
