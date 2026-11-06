# ADR-0001: Local-first evidence processing

**Status:** Proposed — requires Product Owner approval

## Context

Company documentation may contain sensitive network, personnel, vendor and business-process details.

## Decision

Build inference and data storage on the local workstation. Do not send documents to Codex or any remote model; use synthetic fixtures for development. Require explicit checks of any external integrations.

## Consequences

Less compute is available, so start with smaller models and deterministic processing. Development with Codex may require cloud interaction, but that interaction must never include sensitive source documents.
