# Live acceptance run: reproduction record (2026-10-23)

This records a real-model run of the CLI that was performed and checked in the session that wrote this file. It is separate from the earlier run of 2026-10-11 at `96237b1`, which is described in `README.md` and `DIRECTOR_REVIEW_009.md` and was never stored in the repository. Nothing here was copied from that earlier run.

| Item | Value |
|---|---|
| Run date | 2026-10-23, machine clock (run 1 started 19:11:03Z, run 2 started 19:12:05Z) |
| Repository | branch `worker/claude-a`, commit `596a9109332cc174bad36780acdf5e037d8cef8f`, working tree clean before and after |
| Provider / model | Groq, `openai/gpt-oss-120b` (from the stored model responses, not from the CLI text) |
| Platform | Windows, shell `cmd.exe`, Python 3.14.5, pytest 8.4.2 |
| Database | `neptune-postgres` (postgres:16-alpine), host port 5433, reachable. It still held rows from earlier suite runs, so this run's records were selected by creation time. |
| Credential | `GROQ_API_KEY` was supplied as a process environment variable for the session only. It is not in this file, in the captured output, or in any committed file. |

What this is: the CLI output as printed, plus extracts from the persisted `plans` and `turns` records. It is not a verbatim transcript of the model's prompts and responses.

## Run 1: write and read a file

Command (workspace was a new empty temporary directory, shown here as `<TEMP>`):

```text
python -m neptune "Create a file named hello.txt containing hello, then read it and verify its contents." --workspace <TEMP>\neptune-accept-run1
```

Exit code: **0**. CLI output, workspace path shortened:

```text
plan goal-47b2fc8c-plan-1: 4 step(s)
  [completed] create_file: Create hello.txt file
  [completed] write_content: Write 'hello' to file
  [completed] read_file: Read hello.txt
  [completed] verify_content: Verify file contents
RESULT: all steps completed with no tool errors
```

(Per-step tool lines and the model's closing text were also printed; they are consistent with the stored records below and are omitted here.)

Checked independently of the CLI summary:
- **File on disk:** `hello.txt`, 5 bytes, exactly `104,101,108,108,111` (`hello`). It was the only file in the workspace.
- **Persisted plan:** one plan, 4 steps, every step stored with status `completed`, dependencies chained `create_file` > `write_content` > `read_file` > `verify_content`.
- **Persisted turns:** 12 turns, all `completed`, all with `provider_id` `groq` and `model_id` `openai/gpt-oss-120b`.
- **Stored tool calls (all `status: ok`, `outcome: success`):**
  - step 1: `write_file` with empty content (0 bytes) twice, `read_file` returned empty;
  - step 2: `write_file` with `hello` (5 bytes) twice, `read_file` returned `hello`;
  - steps 3 and 4: `read_file` returned `hello`.

Observations to read honestly:
- The planner produced **4 steps**, not the 2 recorded on 2026-10-11. Planning is not deterministic.
- The model repeated work: each of the first two steps issued redundant write/read calls, and step 1 (create an empty file) was followed by step 2 writing the content. The final state was correct, so this is inefficiency, not a defect in the outcome.
- "Completed" still means only that the model stopped without a tool error. The correctness claim above rests on the byte check of the file and the stored tool results, not on the step statuses.

## Run 2: failing command

Command (new empty temporary workspace):

```text
python -m neptune "Run the shell command: exit 3. Then report whether it succeeded." --workspace <TEMP>\neptune-accept-run2
```

Exit code: **1**. CLI output:

```text
plan goal-8d3e0fdf-plan-1: 2 step(s)
  [failed] step1: Execute exit command
      tool run_command: error (command exited with code 3)
  [skipped] step2: Report result
RESULT: not all steps completed
```

Persisted records: plan steps stored as `step1` `failed` and `step2` `skipped` (dependent on `step1`). One turn, `completed`, provider `groq`, model `openai/gpt-oss-120b`, with the tool call `run_command` `{"command": "exit 3"}` and observation `status: error`, `outcome: error`, `exit_code: 3`, `timed_out: false`, `error_message: "command exited with code 3"`. A failing command was reported as a failure at every layer; it was not reported as success.

## Tests run in the same session, same commit

| Run | Result |
|---|---|
| Full suite, Postgres up, no key | 403 passed, 0 failed, 9 skipped (all `GROQ_API_KEY`-gated) |
| Full suite, Postgres up, key set | 412 passed, 0 failed, 0 skipped (126 s) |
| Full suite, Postgres down by mistake (first attempt, discarded) | 359 passed, 53 skipped; not a valid baseline because 44 database tests skipped |

## Evidence classes and limits

- **Reproduced in this session:** both CLI runs above, the on-disk file check, the persisted plan and turn records, and the three suite runs.
- **Not reproduced:** the 2026-10-11 run. Its record in the README, `DIRECTOR_REVIEW_009.md` and the ledger remains a summary from a working session.
- One provider, one model, two goals, Windows only. This is an acceptance check, not a reliability measurement.
- Known limitations are unchanged: shell commands are not confined to the workspace, any tool error ends its step, no plan-level resume, no CI, three older live tests (B-008, B-009, B-011) pass only in suite order on an empty database.
