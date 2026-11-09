# TASK-006C.0: PDF ingestion feasibility and security contract

Date: 2026-11-09 (Europe/Bucharest). Repository: `Y:/Grundschutz-AI`; application: `Y:/Grundschutz-AI/Grundschutz-AI`.

## Outcome and baseline

Completed the bounded architecture/local-tooling assessment and proposed the `pdf-synthetic-ascii/v1` contract in ADR-0007. **No PDF parser or fixture was created and TASK-006C.1 was not started.**

Read-only Git confirmed TASK-006B at `4bbd21f` (`feat: add bounded synthetic XLSX ingestion`) followed by current HEAD `759372c` (`style: remove extra blank line in OOXML safety helper`). The intervening diff removes only two trailing blank lines from `grundschutz_ai/ooxml_safety.py`. Initial working tree was clean. No existing ingestion module, tests, domain or SQLite code/schema was changed in this task.

Created only:

- `docs/decisions/0007-pdf-ingestion.md`: options, recommendation, strict profile, resource/error rules, provenance/reconstruction contract, threat model, independent rendering design and proposed C.1 tests.
- `docs/tasks/TASK-006C0-RESULTS.md`: this local evidence, results, limits and reproduction commands.

No network access, installation/download, source-document inspection, PDF rendering/extraction, OCR, inference/model change, company data, approval pathway, security setting, automatic commit or BSI normative-baseline change occurred. Existing tests use synthetic fixtures only.

## Available local tooling: observed facts

| Check | Observed result |
|---|---|
| Python runtime | 3.12.6, MSC v.1940, 64-bit AMD64; `C:/Python312/python.exe` |
| Normal Python module discovery | No tested PDF module found; user site enabled |
| Isolated Python (`-I`) module discovery | No tested PDF module found |
| PDF-related installed distribution metadata | Empty list in both environments |
| Checked PDF command-line applications on PATH | None found |

Modules checked: `pypdf`, `PyPDF2`, `pymupdf`, `fitz`, `pdfminer`, `pdfplumber`, `pikepdf`, `pypdfium2`, `reportlab`, `fpdf`, `borb`, `pdfrw`, `ghostscript`.

Distribution names were checked for pdf, mupdf, reportlab, ghostscript and borb. Executables checked: `pdftotext`, `pdfinfo`, `pdftoppm`, `pdftocairo`, `mutool`, `qpdf`, `gswin64c`, `gswin32c`, `gs`, `verapdf`. Discovery uses standard-library module specifications/distribution metadata and PowerShell application resolution; it does not run a parser or execute a PDF. No installed library/tool license or version could be inspected because none was found. This is a scoped result for the active Python environments/PATH, not an exhaustive machine-wide software inventory. No user/company directories were scanned for documents or executables.

## Recommendation and dependency limits

Recommend a standard-library, exact synthetic-profile validator/text reader for a separately authorized TASK-006C.1. It must consume a complete canonical PDF representation with strict cross-reference, object, stream, page and text checks. This is moderate bounded-parser/test work, not a regex text scraper or a route to general PDF support. No new dependency is needed for those structural-only experiments.

An existing library/CLI is not a feasible local option under observed tooling. A future offline dependency can broaden support only after explicit approval, an exact version/artifact lock, retained license texts and notices, transitive/native dependency inventory, Python/Windows compatibility and security evaluation. A separate independent renderer is required for visual verification; a text parser alone cannot provide it.

ADR-0007 includes `pypdf==5.1.0` with expected BSD-3-Clause licensing as a **historical comparison-only pin**, not a verified local license finding, current/security recommendation or install approval. No artifact, license file, advisory evidence or numeric production pin was validated offline. Confirm or replace that example from an approved offline artifact before any future dependency adoption. This unresolved gate is stated explicitly rather than treating a remembered version/license as evidence. No requirements file or package configuration was created.

## Supported/rejected profile and security boundary

The proposal accepts only canonical PDF 1.4 test files with one revision/classic xref, a validated flat page tree, one known Courier/WinAnsi font restricted to printable ASCII, uncompressed direct-length streams and fixed single-column visible-text operator sequences. Pages, rows of text and original object/byte positions are explicit. Blank pages/lines remain represented. Unsupported true Unicode, including umlauts/ß, is rejected without replacement or transliteration.

Reject all unknown syntax/objects, scanned/images/vector text, multi-column or reordered text, overlaps, clipping/invisibility/color/alpha/rotation changes, custom fonts/CMaps, forms/annotations/attachments, JavaScript/actions/external references, encryption, signatures/incremental updates, compressed/object/xref streams, malformed or duplicate objects/keys and false offsets/lengths. No repair, OCR, best-effort extraction, skipped pages or partial successful result. Arbitrary ordinary PDFs will almost always fail this synthetic profile.

Proposed caps include 1 MiB original bytes, 16 pages, at most 35 exact indirect objects, 16 KiB per uncompressed content stream, 38 lines per page, 60 ASCII characters per line, bounded grammar tokens/nesting and parent-enforced worker time/output limits. These are contract values, **not implemented or benchmarked safeguards**. Native rendering, hard memory isolation and real-world truth are not established by these limits.

All extracted text remains untrusted. Literal instructions cannot trigger Ollama, HTTP, shell actions, inventory creation or review decisions. Ingestion artifacts have no approved status. Raw diagnostics and rejected/clarification-required candidate fields cannot become approved facts. Future domain use retains exact provenance validation, context/conflict checks and explicit revision-bound human approval; no new review state or approval pathway is proposed.

## Provenance and locator contract

- Retain exact original bytes and binary `pdf_sha256`; a path/hash without bytes is not reconstructible evidence.
- Use the one-based page ordinal from the validated page tree, independent of printed page labels, visual coordinates and physical object order. Preserve blank pages.
- Keep exact page-local text, page SHA-256, ordered line spans, object references and verified raw hex-operand byte spans. Quote offsets are zero-based half-open Unicode code-point offsets within that page; reject cross-page/invented locators.
- Record method/profile and exact parser implementation version, immutable limits, document UTF-8 text SHA-256 and canonical manifest SHA-256. Page text uses LF between lines; the document convenience view uses form feed between pages. The PDF manifest explicitly binds the original binary digest, source ID and ordered structure.
- Verification must retrieve/hash original bytes, rerun the same compatible parser/policy and compare all regenerated pages/text/locators/manifest. Keep source revisions/history and operational timestamps separately. Hashes provide integrity identifiers, not author authentication or factual truth.

No persistence is implemented: SQLite schema version 1 and the existing UTF-8 Evidence source-hash/character-locator contract remain unchanged. A future source-store/adapter decision must bind PDF binary identity and page/context manifests without substituting a binary hash for a text hash or dropping contradictory page/document context.

## Independent rendering: unresolved check

**Not performed: no independent renderer was found.** Structural extraction and visual correctness must have separate acceptance results. A future approved offline renderer should use the same captured bytes in a bounded process, with pinned version/artifact/fonts/configuration, no actions or resource/network fetching and explicit page/image hashes. Compare all page rasters manually with expected text and line positions; no OCR is proposed. Known synthetic golden rasters need independently specified expected values and human review. Pixel hashes alone do not prove text equivalence or correct reading order.

Hidden, extra, absent, clipped or overlapping glyphs can become visible discrepancies, but rendering does not prove source truth or universal hidden-content absence. Missing/substituted fonts, warnings, mismatches or inconclusive/unavailable checks block a visually verified-evidence claim and require clarification before downstream use. A successful rendering check never approves inventory.

## Proposed C.1 tests and remaining gates

ADR-0007 specifies positive ASCII multi-page/blank-page fixtures, exact offsets/order/hash/reconstruction tests and negative Unicode/font/layout/scan/active-content/incremental/xref/malformed-object/resource tests. It includes late-page failure with no partial output, worker timeout/output tests, inert prompt-injection text, frozen outputs/no side effects and independent visual comparisons when an approved renderer exists. **No PDF tests were implemented or run in this architecture task.**

Remaining gates:

1. Human review and a separate instruction for C.1, accepting or amending the deliberately narrow ASCII/canonical grammar. Its exact fixture spelling still needs to be finalized with implementation tests.
2. Implementation and adversarial tests of full byte/object coverage, page/quote mapping, resource enforcement and Windows worker lifecycle; no safety behavior is claimed as implemented here.
3. An independently approved renderer/artifact/font/license lock and actual visual validation before claiming visually verified PDF evidence. Current local absence is unresolved, not a pass.
4. For broader PDFs: an approved offline dependency with a validated exact version/hash/license/security/compatibility record and a separately reviewed richer profile. The historical comparison pin does not close this gate.
5. Source authentication, protected source storage, authenticated reviewers, local attacker/race protection, fuzzing, Unicode/rich-layout handling and future adapter/migration design remain outside this prototype.

C.0 documentation and local feasibility checks are complete for review; PDF runtime correctness, rendering equivalence and production readiness are not established. No automatic continuation to C.1 or BSI certification/baseline approval follows.

## Existing offline suite

Executed from the application directory:

```powershell
py -3.12 -m unittest tests.test_domain tests.test_extraction.ClientTests tests.test_extraction.ValidationTests tests.test_storage tests.test_docx_ingestion tests.test_xlsx_ingestion
```

Observed: **235 tests in 1.884 seconds; OK; zero failures and errors**. All existing domain, extraction unit, SQLite, DOCX and XLSX tests were preserved. Optional live Ollama classes were not selected. No application behavior was changed.

## Exact reproduction commands

```powershell
Set-Location Y:/Grundschutz-AI/Grundschutz-AI
py -3.12 -m unittest tests.test_domain tests.test_extraction.ClientTests tests.test_extraction.ValidationTests tests.test_storage tests.test_docx_ingestion tests.test_xlsx_ingestion -v
```

Run the following discovery snippet first with normal Python as shown, then replace the final command with `py -3.12 -I -` to repeat in isolated mode. It reads local Python metadata only:

```powershell
@'
import importlib.metadata as metadata
import importlib.util
import json
import site
import sys
names = ('pypdf', 'PyPDF2', 'pymupdf', 'fitz', 'pdfminer', 'pdfplumber',
         'pikepdf', 'pypdfium2', 'reportlab', 'fpdf', 'borb', 'pdfrw', 'ghostscript')
print(json.dumps({
    'python': sys.version, 'executable': sys.executable,
    'user_site_enabled': site.ENABLE_USER_SITE,
    'modules': {name: (None if (spec := importlib.util.find_spec(name)) is None
                       else spec.origin) for name in names},
}, indent=2))
print('PDF-related distributions:', [
    (dist.metadata.get('Name'), dist.version)
    for dist in metadata.distributions()
    if any(term in dist.metadata.get('Name', '').lower()
           for term in ('pdf', 'mupdf', 'reportlab', 'ghostscript', 'borb'))
])
'@ | py -3.12 -

$taskPdfTools = 'pdftotext','pdfinfo','pdftoppm','pdftocairo','mutool','qpdf','gswin64c','gswin32c','gs','verapdf'
foreach ($taskPdfTool in $taskPdfTools) {
    $taskFound = @(Get-Command -Name $taskPdfTool -CommandType Application -ErrorAction SilentlyContinue)
    if ($taskFound.Count -eq 0) {
        Write-Output "$taskPdfTool : NOT FOUND ON PATH"
    } else {
        $taskFound | Select-Object Name,Source,Version | Format-List
    }
}
```

Read-only Git reproduction from the repository root:

```powershell
Set-Location Y:/Grundschutz-AI
git log -2 --format="%h %s"
git diff --ignore-all-space --ignore-blank-lines --exit-code 4bbd21f..HEAD
git status --short --untracked-files=all
git diff --check
git diff --name-only
```

These commands make no package/network calls and do not alter Git configuration. If the execution sandbox encounters Git's ownership guard, use the normal user read-only execution context; do not change safe.directory or ownership/security settings.

## Final Git verification

Final read-only status:

```text
?? Grundschutz-AI/docs/decisions/0007-pdf-ingestion.md
?? Grundschutz-AI/docs/tasks/TASK-006C0-RESULTS.md
```

HEAD remains `759372c`. `git diff --ignore-all-space --ignore-blank-lines --exit-code 4bbd21f..HEAD` produced no differences. `git diff --name-only` and the explicit application/tests diff were empty. `git diff --check` passed; both new/untracked documentation files also passed direct strict UTF-8, trailing-whitespace and final-newline checks. Read-only Git ran as the normal user without ownership/configuration/security changes. No files staged or committed and no unrelated working-tree changes.
