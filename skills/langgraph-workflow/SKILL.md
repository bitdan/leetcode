---
name: langgraph-workflow
description: Run the repository's general-purpose LangGraph text workflow as a reusable skill entrypoint. Use when the task should go through the existing generate -> critique -> refine workflow instead of a specialized skill such as LeetCode coaching or stacktrace analysis.
---

# LangGraph Workflow

## Overview

This skill wraps the repository's generic LangGraph workflow behind a stable script entrypoint so API and agent layers
can invoke it consistently through `skills/` instead of importing implementation modules from `py/`.

## Scripts

- Use [scripts/run_workflow.py](scripts/run_workflow.py) as the stable entrypoint.
- Core workflow logic lives in [scripts/workflow_core.py](scripts/workflow_core.py).
