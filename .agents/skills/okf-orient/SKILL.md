---
name: okf-orient
description: Find and read honeycomb-hacs's documentation in okf/ before working. Use at the start of any task in this repository, before answering how the integration works or why it is built that way, before planning or changing code, and whenever you are unsure which decision governs something.
---

# Orient in the okf/ bundle

`okf/` is the single source of documentation for this repository. Read the part your task needs
before you plan or edit; the docs record intent and constraints the code cannot show.

## Read in this order, and stop when you have enough

1. `okf/index.md`: the map.
2. `okf/system/overview.md`: the parts and the repository map.
3. `okf/process/working-in-this-repository.md`, before changing anything.
4. The decisions in `okf/decisions/` that govern the area you are touching.
5. `okf/spec/01-telemetry.md` for anything about what is sent; `okf/spec/02-roadmap.md` for what
   is built and what is next.

## Where each answer lives

| You need | Read |
|---|---|
| What the integration is for, and is not | `okf/project/charter.md` |
| Which events become spans, their attributes, what is excluded | `okf/spec/01-telemetry.md` |
| Why something is built the way it is | `okf/decisions/index.md`, then the record |
| What is built, what is next, open questions | `okf/spec/02-roadmap.md` |
| Running the tests, CI | `okf/operations/local-development.md` |
| Releasing for HACS | `okf/operations/releasing.md` |
| What may never be committed, and the checks | `okf/operations/security-checks.md` |

## When sources disagree

- **Code** is the truth about what the integration does now.
- A **decision** is the truth about what it should do. If code contradicts one, tell the person,
  and fix the code or revise the decision with `okf-decision`.
- The **spec** describes the intended behaviour; correct it in the same change with `okf-update`.
- The **charter** has final authority on intent.

## After you orient

- Before finishing any change, use `okf-update`.
- When the work makes or reverses a durable choice, use `okf-decision`.
- Never write session notes, task logs or to-do lists into the repository. It is public.
