# Phase prompt template

Use this when asking Claude Code to plan or implement the next phase.

## Planning prompt skeleton
Read CLAUDE.md first.
Inspect the current branch and latest SOT.
Do not code yet.

Return:
A. exact phase scope
B. exact file list touched
C. exact order of edits
D. cleanup vs structural changes
E. validation checklist
F. remaining risks
G. expected visible changes
H. key features to check
I. what to do next

## Implementation prompt skeleton
Read CLAUDE.md first.
Implement approved Phase X only.
Stay within scope.
After implementation, summarize:
- files touched
- risks encountered
- expected visible changes
- key features to check
- what to do next
