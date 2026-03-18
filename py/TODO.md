# Py AI TODO

## Summary

### Priority 1

- [ ] Build `leetcode_coach`
  Input: LeetCode problem statement plus user code
  Output: hints, complexity analysis, bug/risk points, and improvement suggestions
- [ ] Make `leetcode_coach` a real LeetCode study companion instead of a plain chat API
- [ ] Support staged guidance so the user learns the problem rather than getting the full answer immediately

### Priority 2

- [ ] Build LangGraph-based agent workflows
- [ ] Candidate workflow: problem -> reasoning hint -> code review -> retry advice -> summary
- [ ] Candidate workflow: stacktrace/log -> root cause -> fix suggestion -> patch draft

### Priority 3

- [ ] Build vertical RAG for code, Java/Spring errors, and LeetCode notes
- [ ] Index solved problems, templates, common mistakes, and explanations
- [ ] Retrieve similar problems before generating guidance

### Priority 4

- [ ] Add evaluation, tracing, and benchmark support
- [ ] Measure SQL generation quality, stacktrace diagnosis accuracy, and coach guidance quality
- [ ] Track prompt, tool calls, latency, token usage, and failure reasons

## LeetCode Coach

Conclusion: yes, this can be built as a LeetCode companion focused on helping users learn how to solve problems.

### Target Value

- [ ] Help the user understand the problem
- [ ] Help the user form an approach instead of directly exposing the final solution
- [ ] Help the user review their own code and iterate
- [ ] Help the user build reusable patterns for similar questions

### Core Capabilities

- [ ] Problem explanation
  Rewrite the problem in simpler language and extract constraints, inputs, outputs, and edge cases
- [ ] Progressive hints
  Give level 1 to level N hints from high-level direction to near-solution guidance
- [ ] Complexity analysis
  Explain time complexity, space complexity, and whether the solution matches expected constraints
- [ ] Code review
  Identify bugs, boundary-condition misses, unnecessary work, and style/readability issues
- [ ] Improvement suggestions
  Compare current approach with better approaches and explain why they are better
- [ ] Similar-pattern coaching
  Link the current problem to patterns like binary search, sliding window, DFS/BFS, DP, monotonic stack, and greedy
- [ ] Retry guidance
  After a failed attempt, tell the user what to fix next instead of dumping the full answer
- [ ] Post-problem summary
  Generate a compact "what you should remember" note after each problem

### Suggested Modes

- [ ] Hint mode
  Never reveal full code unless the user explicitly asks
- [ ] Review mode
  Focus on the user's submitted code
- [ ] Teach mode
  Explain why the common approach works
- [ ] Mock interview mode
  Ask leading questions and reveal hints gradually

### Suggested Inputs

- [ ] Problem title
- [ ] Problem statement
- [ ] Constraints and examples
- [ ] User code
- [ ] Language
- [ ] User question or difficulty point

### Suggested Outputs

- [ ] One-paragraph problem understanding
- [ ] Key observations
- [ ] Hint level
- [ ] Complexity judgment
- [ ] Review findings
- [ ] Next-step suggestion
- [ ] Similar-pattern recommendations

### Implementation Ideas In This Repo

- [ ] Add `py/api` endpoint for coach requests
- [ ] Add `py/langgraph` workflow for staged hinting and review
- [ ] Add optional `py/mcp_server` tool so external AI clients can call the coach
- [ ] Add tests for hint mode, review mode, and complexity analysis
- [ ] Keep prompt design strict: default to teaching, not directly solving

### First Deliverable

- [ ] MVP: submit problem + code -> return:
    1. understanding
    2. hint
    3. complexity analysis
    4. code review
    5. next-step advice
