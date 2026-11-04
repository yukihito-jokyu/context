# Collecting feedback during use

This document explains how a skill made with skill-foundation collects the feedback it receives while it is used. The AI reads it when it follows the hooks' guidance (additionalContext) and when it checks the records. The skill's procedure (SKILL.md) does not refer to it.

Read it in this order. Chapter 1 covers why and what is collected, chapter 2 how it is kept apart from the skill's own work, chapter 3 when it is collected, chapter 4 the AI's commands, chapter 5 the review page and approval, chapter 6 the record format, chapter 7 how to turn it off and its limits, and chapter 8 how to use the collected feedback for improvement.

## 1. Why and what

A skill's Eval is made with the user when the skill is created. Feedback such as "this is wrong" that arrives later, during real use, is lost if it is only fixed in the conversation. The same feedback then comes back from other people and sessions, and nobody can later check which version received which feedback, how it was fixed, and whether the user accepted the fix.

So the following four things are saved in the same format for every skill:

- The feedback, word for word (the user's own message)
- The outputs before the fix (the version that received the feedback)
- The outputs after the fix (the versions presented in response)
- The user's approval (only one given with the button on the review page)

Approved cases later become material for Eval and convergence-test candidates.

## 2. Kept apart from the skill's own work

Collection is an add-on provided by the hooks and is kept fully apart from the skill's own work.

- SKILL.md, the rule table, and the checklist contain no collection instructions and no collection rules (`skill_lint.py` checks this). The AI is told what to do only through the hooks' additionalContext
- `run.py` start, check, and finish never call collection
- Turning the hooks off removes both collection and the guidance; only the skill's own generation, checks, and finish run
- A collection failure never stops the checks or finish. `hook.py` discards every exception from `feedback.py`

They are kept apart so that collection never gets in the way. If collection were part of the procedure, it would add variance to the outputs, and a collection bug could stop the skill.

## 3. When it is collected

`hook.py` calls `feedback.py` for each hook event.

| Event | Behavior |
|---|---|
| Stop (before ending a reply) | When the run finishes (`done`) or waits for a question (`waiting`), saves the presented outputs (contract outputs changed since start) and the skill's files and contract, with their content. This is called a version (delivery). If there is open feedback, a version whose outputs changed is added to it as a fix |
| UserPromptSubmit (a user message) | For messages after outputs were presented in the same session, records the message word for word and the version presented at that time. Tells the AI how to classify it through additionalContext. The message is never blocked |
| PreToolUse (before an edit) | Denies direct edits of the collection records (`.skill-feedback/`) with edit tools |

Messages are recorded only within these limits:

- Messages during a run (`active`) are not recorded. They continue the request rather than give feedback on presented outputs
- Only messages in the session that presented the outputs are recorded
- Without open feedback, only the first three messages after a presentation are recorded. Later messages are treated as another topic

## 4. The AI's commands

When the hooks' guidance arrives, classify the message before replying. The AI may classify it, but must not replace the original text with a summary.

| Situation | Command |
|---|---|
| Feedback on the outputs (wrong, missing, please change) | Before editing: `python3 <skill>/scripts/feedback.py feedback --event <message-ID> --summary "<gist>"` |
| Not feedback | `python3 <skill>/scripts/feedback.py ignore --event <message-ID> --reason "<reason>"`. The original text is kept |
| An input file you read to fix the outputs | Before changing it: `python3 <skill>/scripts/feedback.py context --file <path>` |
| After fixing | At the end of the reply, run `python3 <skill>/scripts/feedback.py review` and give the user the URL it prints |
| Checking the records | `feedback.py status` (unclassified messages, open and approved feedback), `feedback.py validate` (format and references) |
| Using it for improvement (only when the user asks) | `feedback.py export --out <new directory>` (chapter 8) |

Recording feedback creates a case whose "before" is the version that received the feedback. Further feedback on the same version is added to the same case. Fixed outputs are saved as a fix automatically, at the next Stop or when `feedback.py review` runs. If the skill is run again to fix the outputs, the finished version becomes the fix.

Only people approve. The AI does not press the approve button or post to the approval URL. An "OK" in the conversation, no answer, or the AI's own judgment is not an approval. Do not leave the work unfinished only to wait for an approval.

## 5. The review page and approval

`feedback.py review` starts the review page server (`feedback_review.py`) in the background, prints its URL, and returns. The server listens only on `127.0.0.1` and stops after 30 minutes without requests. After it stops, the same command starts it again.

For each case, the page shows the feedback word for word, the versions, and the actual files before the fix and in the newest fix. Text appears as a diff and as full text, HTML as a preview with scripts disabled, images as images, and PDFs and other files as links to the actual files. When the user presses "Approve this fix", that version is recorded as the answer to the feedback.

An approval is rejected in any of these cases, and the page asks the user to reload and check the current content:

- The sender (Origin and Host) is not this review page
- The token is not the one issued when the case's page was last opened. A token is issued each time the page opens and can be used once. After the server restarts, earlier pages cannot approve
- The version being approved is not the version shown on the page, or not the newest fix
- The actual files in the project changed after the page was opened

The page can be reopened any number of times. Reopening first saves the current files as a fix and issues a new token.

## 6. The record format

Records live in `.skill-feedback/<skill name>/feedback.json` in the working project. The actual output and skill files are saved byte for byte in `objects/<sha256>`, so earlier versions survive renames and edits. `.skill-feedback/.gitignore` keeps the records out of Git. Records are only appended, never overwritten by a new run or a rerun. The format is `assets/feedback.schema.json` (`schema_version: 1`), checked by `feedback.py validate`.

| Element | Content |
|---|---|
| `messages` | Messages word for word, and approvals with comments from the review page. Time, product, session, presented version (`delivered`), classification (`class`) |
| `deliveries` | The presented outputs (`files`), the run (`run`), the original request (`request`), the normalized input (`input`), input files (`input_files`), the skill version (`skill`), the contract version |
| `cases[].issue` | The feedback word for word (`quotes`), its gist (`summary`), and the message IDs it came from |
| `cases[].before` | The delivery ID of the outputs that received the feedback |
| `cases[].revisions` | The versions presented in response, in order |
| `cases[].after` | The delivery ID the user approved (null if not approved) |
| `cases[].approval` | Time, comment, approved delivery ID, and sender of the approval (null if not approved) |

The skill version is the hash of the list of the skill's files (excluding `dev/` and `settings/user-setting.yaml`). The list itself is also saved in `objects/`, so the skill as it was can be recovered.

Records made by tests carry `synthetic: true`, and approvals copy the mark, to tell them apart from real users' approvals. New records get it when the environment variable `SKILL_FEEDBACK_SYNTHETIC=1` is set.

## 7. Turning it off and limits

Collection stops in any of these ways:

| How | Result |
|---|---|
| Set `control.feedback` to `false` in the spec | It goes into the contract; `hook.py` does not collect and `install.py` does not register collection |
| `install.py --no-feedback` | Registers the output-check hooks without collection (the registered commands get `--no-feedback`) |
| `install.py --no-hooks` | Registers no hooks at all, including collection. Checks run only through `run.py check` and `finish` |

To use only collection, `install.py --features feedback` registers three hooks, without the after-edit hook (PostToolUse).

The records are treated as local. Strict user authentication and protection against edits from the shell are out of scope. Chat-only replies are not saved; a skill that wants them saved defines a destination in its output contract. Mark binary outputs such as images with `binary: true` in the contract's output. They are not checked as text; only `command` checks apply.

## 8. Using the collected feedback for improvement

`feedback.py export --out <new directory>` exports only approved feedback. Feedback waiting for approval and unapproved fixes are left out. The export has the following layout, and its references and file contents (sha256) are checked after exporting.

| Location | Content |
|---|---|
| `dataset.json` | For each case: the feedback word for word (`issue`), the approval (`approval`), the original request and input values, the file lists of the version before the fix (`before`) and the approved version (`after`), the input files, and the skill version at the time |
| `cases/<case>/before/`, `after/`, `inputs/` | The actual files before the fix and in the approved version, and the input files (the earliest saved copy) |
| `skills/<version>/`, `skills/<version>.manifest.json` | The skill's files when the feedback arrived, and their list |

skill-foundation's `feedback_eval.py` turns the export into Eval and convergence-test candidates. How to work on a copy without changing the original skill, and why an approval is not treated as agreement to an evaluation condition, is in chapter 9 of skill-foundation's `references/eval.md`.
