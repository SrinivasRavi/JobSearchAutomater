## Project
JobSearchAutomater is a private, local-first job discovery and application automation system.

Current priority:
- Build progressively.
- Keep scope tight.
- Prefer working code over broad speculative architecture.

## Ground rules
- You will be running as "claude --dangerously-skip-permissions" so do not stop and ask permissions for everything. The only exception is first you declare the architecture and plan, before writing code.
- Before you return control back to me in the terminal everytime, please commit to git and push to remote always (https://github.com/SrinivasRavi/JobSearchAutomater.git). Test pushing the very initial version too. That way I can traceback our interactions and the states of all the docs - mainly dreaming-doc.md which is a live doc like other docs, but probably going to last the entire project, reflecting changes in our "dream" for the project and any plans.  
- Treat `docs/dreaming-doc.md` as the long-term product vision. You must go through it at the start of each sprint for context.
- Treat `docs/current-sprint.md` as the source of truth for what to build now. Every sprint will have a new current-sprint.md written by the you at the end of a sprint. Note, I will also clear your context window after each sprint. So please persist to dreamin-doc and current-sprint correctly then.
- Do not implement future milestones/sprints unless explicitly asked.
- If requirements are ambiguous, ask before coding.
- Prefer deterministic code and APIs over LLM-based logic where possible.
- Keep changes minimal and local.
- Do not rewrite large unrelated areas of the codebase.
- Do Test driven development, have the unit and integration tests in place before developing the code.

## Current product priorities
1. Capable scraper.
2. Reliable persistence and dedupe.
3. Capable form-filler / auto-applier.
4. Tracking and analytics are secondary support capabilities.

## Scope discipline
- Work in small vertical slices.
- One task per session when possible.
- Do not "helpfully" add extra features outside acceptance criteria.
- Do not prematurely build v3/v4/v5 ideas into v1/v2 code unless explicitly requested.
- When asked to build something, first provide a short plan unless the user explicitly asks for immediate implementation.

## Architecture principles
- Scraper and applier must remain separate modules/services.
- Keep source-specific logic isolated behind adapters.
- Prefer simple interfaces over abstraction-heavy frameworks.
- Local-first and $0 budget bias.
- Robustness matters: log errors, isolate failures, avoid crashing the whole system.

## Duplicate handling
- A single scraper instance must never persist the same job twice.
- For now, cross-workflow duplicate jobs/applications may exist in later milestones unless current sprint says otherwise.
- Use the clean job link as the current dedupe key unless a sprint doc overrides it.

## Success criteria mindset
Primary success:
- The system discovers relevant jobs and submits applications correctly, completely, and in a timely manner using the intended UserProfile.

Secondary signals:
- Recruiter responses, HR calls, rejection emails, and other downstream outcomes.

## Working style
For each task:
1. Read `docs/current-sprint.md`.
2. Read only the relevant parts of `docs/dreaming-doc.md` if needed. But when your context window is empty, read it fully to understand what we are trying to build eventually.
3. Restate the task briefly.
4. List files you plan to change.
5. Give a short plan.
6. Implement only after approval, unless user asked for direct coding. No need to stop to ask permissions then.
7. Update `docs/progress.md` after finishing.

## Code expectations
- Prefer readable, boring code over clever code.
- Keep functions small and easy to test.
- Add or update tests when practical for the task.
- Log failures with enough detail to debug later.
- Do not add comments that restate obvious code.
- Do not leave TODOs unless they are added to `docs/todo.md`.

## Docs expectations
When you complete a task, update `docs/progress.md` with:
- what changed,
- decisions made,
- blockers,
- next recommended task.

If a new important rule is discovered repeatedly, suggest updating `CLAUDE.md` rather than repeating it in chat.
