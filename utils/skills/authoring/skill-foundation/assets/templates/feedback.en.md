# Collect feedback and approved artifact revisions

Every generated skill must bundle the shared feedback hooks and register them by default. This is an optional runtime extension: users may disable hooks, including with install.py --no-hooks. Never add collection duties to SKILL.md, its rules or its checklist. Only enabled hooks inject instructions through additionalContext; collector failures must not prevent the core skill from completing. Use `scripts/feedback.py` and `assets/feedback.schema.json` (schema_version: 1). Keep one common format across skills.

## During use

1. `run.py start` creates the normal run ID; enabled hooks inject input-capture guidance. Before changing input files, save their actual bytes with `python3 <skill>/scripts/feedback.py context --file <input-file>`. Save permitted external inputs locally before recording them.
2. The Stop hook saves presented artifact bytes, request, normalized inputs, contract and the skill files used, after completion or while waiting. The core run.py commands never call the collector.
3. UserPromptSubmit records the original user message and the revision already presented. When it is feedback, run `python3 <skill>/scripts/feedback.py feedback --event <message-ID> [--summary <summary>]` before editing. For unrelated messages use `ignore --event <message-ID> --reason <reason>`. Both preserve the original message.
4. Correct the artifact and present it. Run `python3 <skill>/scripts/feedback.py review --port 0` in a persistent terminal and share the localhost URL. The user compares the original feedback and actual before/after files on that page. A new run can continue the same feedback case. Do not keep artifact generation unfinished solely to wait for approval.
5. The user presses the approval button on that page. The server links the operation and optional comment to the exact displayed revision. It rejects stale pages and changed files. Chat acknowledgments, silence and assistant decisions are not approval. The assistant must not operate approval controls or POST to the approval API. Only synthetic tests may simulate approval; never report those as real human approvals.

The core start/check/finish commands do not import or call the collector and work without hooks. Extension metadata belongs to the collector, never to the core run state. Output enforcement runs while the skill is active. Feedback collection continues after completion. Skill files remain editable. Direct editing-tool changes to run and feedback records are rejected.

Use `feedback.py status` to view pending cases and unclassified messages; `validate` checks stored content and references. Records live under the project-local `.skill-feedback/<skill-name>/`, excluded from Git by its own `.gitignore`. Starting or restarting a run does not overwrite the history.

The page listens only on `127.0.0.1` and checks the origin, revision and one-use token. It shows text/diffs, images, isolated HTML previews and original file downloads. Close the server with Ctrl+C; stored records remain. Declare binary outputs with `outputs[].binary: true` and command-based checks/formatting.

## Shared structure

`feedback.json` links `messages`, `deliveries`, and `cases` by ID. Each case contains the original `issue`, a `before` delivery, presented `revisions`, an approved `after` delivery, and the review-page `approval` operation/comment. Pending cases have null `after` and `approval`.

Deliveries preserve the original request, inputs, captured input files, actual skill files and contract. Artifacts including images and PDFs are kept as original bytes under `objects/<sha256>`. Snapshots survive file replacement. Approval links an observed event to stored content; this does not provide strong user authentication or prevent shell-based rewriting of local records. Synthetic hook tests are not real user approvals. Chat-only results must first be written to a file defined by the skill's output contract.

## Build improvement Evals and convergence tests

```bash
python3 <skill>/scripts/feedback.py export --out <new-dataset-directory>
python3 <foundation>/scripts/feedback_eval.py --dataset <dataset> --skill <source-skill> --out <new-workspace>
```

Export includes approved cases only, with original feedback, approval, before/after bytes and skill versions. The preparation command creates a working skill copy and draft Eval/convergence inputs. It does not edit the source skill or its existing Eval.

Artifact approval is not approval of generalized criteria. Review the draft questions with the user: how broadly the feedback applies, pass/fail examples, target outputs, judging method and missing reproduction inputs. Run `eval_check.py` after that review; convergence preparation rejects pending Eval questions. For binary artifacts choose a judge that can inspect the actual files, rather than scoring binary bytes as text.

Use the foundation Eval and convergence workflows. Add typical/default/edge/holdout tasks beyond collected examples. Producers receive only the original request and inputs, never feedback, approved corrections, expected outputs or grading criteria. A separate evaluation role compares the original and candidate skill using the same approved Eval. Follow the existing confirmation rules for independent model-run counts before executing models.

Hook protocol checked 2026-10-31: [OpenAI Docs](https://learn.chatgpt.com/docs/hooks#userpromptsubmit), [Claude Code Docs](https://code.claude.com/docs/en/hooks#userpromptsubmit). UserPromptSubmit supplies `prompt`; `hookSpecificOutput.additionalContext` can request classification without blocking the user's message.
