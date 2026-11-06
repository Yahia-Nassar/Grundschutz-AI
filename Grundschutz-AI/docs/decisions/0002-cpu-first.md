# ADR-0002: CPU-first local inference

**Status:** Proposed — benchmark in Sprint 1

## Context

Target is Windows 11, 16 GB RAM, AMD Radeon RX 580 with 8 GB VRAM. RX 580 is absent from the currently listed official Ollama AMD ROCm Windows supported GPUs.

## Decision

Use a small quantized model as the baseline and test CPU performance first. Investigate Vulkan separately as an optional acceleration path. No assumed GPU performance or automatic GPU requirement.

## Consequences

Latency may be high; queue inference, process documents in batches, keep retrieval context constrained, and prefer deterministic logic for document assembly. Record the CPU type and RAM/latency numbers before choosing a model.

Official GPU docs: https://docs.ollama.com/gpu
