# Acceptance and quality gates

## Always

- Every company-derived claim has an evidence locator; unsupported claims are flagged.
- No invented assets, dates, personnel, vendors or source citations.
- No document text leaves the workstation through application inference.
- Tests and fixtures are synthetic until explicit approval for a controlled pilot.

## Sprint 0

- README, AGENTS, GOALS, PLANS and architecture document are present and coherent.
- `A1_REQUIREMENTS.md` maps the 8 official reference positions and 9 information themes correctly.
- Python 3.12, Git, VS Code and Codex are operational.
- First Git checkpoint exists, `.gitignore` excludes sensitive/generated paths.
- No application code or downloaded LLM models.

Sprint 0 acceptance also requires recorded primary-source verification and the applicable BSI baseline decision, plus Product Owner review of the evidence in `PLANS.md`. Missing or blocked checks are not passes. Human approval is required before Sprint 1; this review does not authorize installations or model downloads.
