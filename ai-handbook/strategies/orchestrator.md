# Orchestrator

If the user says start, continue, or do it, and does not name a strategy, follow this file. Those words fill the pool from packages already open and from the next list. The orchestrator does not ask which strategy, which model, or which package. A new fact arrives as its own message. Packages on the Huge card stay there until that check is answered. Continue does not stop to ask it.

1. Packages that may be opened are the Order section of `CONSTITUTION.md`. Small and `small-low` may sit beside other work. Up to five `medium` or `medium-low` packages may be open. The cap was raised from three by the user. A `large` or `large-low` package does not share the session with a second `large` or `large-low` package. A `huge` package may sit beside other work. It does not use the large cap. Before its task force is chosen, name one mature Python or Rust library that could stand in, or say there is none. A library already under `native` is named from that list. A new library is asked, as Routing in `CONSTITUTION.md` says, and is not written to `cran/replaced.json` until agreed. A resemblance is not enough to call the package done. If a library might stand in, the package stays on the Huge card and is not opened. The task-force model is not assigned until that check says there is no stand-in.
2. Each opened package uses the strategy stored on it. Read that one strategy file. Do not use a `*-low` strategy on a package with no Fortran and no C that computes, and do not use `small`, `medium`, or `large` on a package that has one.
3. Assign only functions whose `blocked_by` is empty and whose `assigned` is empty. The model is the first line below that matches. It is the agent's model argument. There is no model field on the function. Before a launch, set `assigned` to that agent. Translation batches pass that slug on the Task `model` argument. Do not use `inherit` for translation batches.

- A miss named in `strategies/hard-function.md` is not started. No model.
- `strategies/hard-function.md`, and a sub-agent already failed that function once: stop and report. No model.
- `strategies/hard-function.md`, first retry: `claude-haiku-5-5-thinking-high`, once.
- A new crate, and no experience filename describes that kernel: `claude-haiku-5-5-thinking-high`.
- A crate whose family is already an experience file: `claude-haiku-5-5-thinking-high`.
- A crate proof failed once: `claude-haiku-5-5-thinking-high`, once, then stop.
- Choosing a task force for `large`, or for `huge` after the stand-in check says there is none, before any function is translated: the orchestrator names the related functions in this session, or one `gpt-5.6-luna-medium` sub-agent whose only job is to name those groups. It does not write them.
- Numerical Python with no matching filename. A fit, a distribution, a linear-algebra routine, or an optimizer: `gpt-5.6-luna-medium` when the launcher accepts that slug, otherwise `claude-haiku-5-5-thinking-high`.
- Any other Python with no matching filename. The agent may write the one new lesson: `gpt-5.6-luna-medium` when the launcher accepts that slug, otherwise `claude-haiku-5-5-thinking-high`.
- Python, and an experience filename matches: `claude-haiku-5-5-thinking-high` when the launcher accepts that slug, otherwise `gpt-5.6-luna-medium`.

Easier batches use Luna: `python-numerical` and `python-other`. Skilled batches use thinking Haiku: `python-match`, and the crate and hard-function lines above. The plain slug `claude-haiku-5-5` is not passed to Task; when Settings names Haiku without `-thinking-high`, use `claude-haiku-5-5-thinking-high`.

`claude-fable-5-1-thinking-high`, `claude-haiku-5-5`, `cursor-grok-4.6-high-fast`, `muse-wonder-1.0-high`, `grok-4.7-high-fast`, and `composer-2.5-fast` are not used. A cheaper model on the list already covers those jobs.

## Assignment

Classify each Python batch before choosing the model line. `python-match` when a filename in `experience/` or `packages/<Name>/experience/` already describes the pitfall for this function. `python-numerical` when there is no such filename and the work is a fit, a distribution, a linear-algebra routine, or an optimizer. `python-other` for any other Python with no matching filename. Crate and hard-function lines above set their own tasks.

List at most three experience filenames for the launch prompt by scanning those directories without opening the files. A name matches when its words describe the same pitfall as the function, its R help, or its source file, not when it merely shares the function name.

Resolve the Task slug before launch. Use the slug from the first matching line above. If Task rejects that slug, walk the `otherwise` chain on that same line for numerical Python, or the next fallback named on lines 16 to 18, until one slug is accepted. One slug per launch.

Before filling the pool, run `python3 dashboard/build.py --cost-advice`, or read the Cost band on the home page after `--home`. For each task, skip models listed under `set_aside` and prefer `recommended` when it differs from the default.

Each finished batch appends one object to `dashboard/launches.json` with `model`, `task`, `minutes`, `r_lines`, `matched_lines`, `functions`, `matched`, and `returned` as an ISO timestamp. Lines 9 and 10 do not append a record. The task names for lines 11 to 18 are, in that order, `hard-retry`, `crate-new`, `crate-family`, `crate-retry`, `task-force`, `python-numerical`, `python-other`, and `python-match`. Older rows may still say `hard-opus`; treat them like `hard-retry` for yield.

The launch prompt names the package, the functions in the batch, the strategy filename, and at most three experience filenames. The orchestrator matches those names from the directory listing and does not open the files. The sub-agent opens at most three. The prompt does not carry lesson bodies, dashboard HTML, or the rest of the package.

`strategies/hard-function.md` is one named function. It is not a pool.

If Fortran or C that computes turns up in `small`, `medium`, or `large`, stop the plain work and set `strategy` to the matching `small-low`, `medium-low`, or `large-low` name.

Open a reported package before more of the package that is waiting on it.

The fleet target is **25 running sub-agents** at all times. A running agent is a Task launch whose `assigned` id is still set on at least one untranslated function. A stored `assigned` id stays a lock. Continue does not clear an id it did not write. A batch is one agent, and a small package is still one agent. Most matched-experience batches are `claude-haiku-5-5-thinking-high` when the launcher accepts that slug, and otherwise `gpt-5.6-luna-medium`. Most first-lesson and numerical batches are `gpt-5.6-luna-medium`. Grok and Composer are not used.

A batch returns three things: the proof result, any package names it is waiting on, and the experience path it created or edited, or none. The sub-agent writes that one lesson itself before it returns. The orchestrator records the check, clears `assigned`, and writes `blocked_by`. The next batch sees that new file by its filename. It is not given the lesson bodies from the previous batch.

When several agents return in the same turn, record every return, then run `python3 dashboard/build.py --home` once. The next function is chosen from `assigned` and `blocked_by` in that package's `translation.json`. The pages `--home` wrote are the display. They are not opened to choose the next function. **After each return**, count running agents (UUID `assigned` on untranslated functions). While that count is below **25** and a function is doable, start the next batch under the model order. Launch one batch per return first; if several return together, launch enough batches to bring the fleet back to 25 or until nothing is doable. If the fleet is already at 25 or above, wait for the next return before launching again. If nothing is doable, leave slots empty. Do not start an agent only to file the lesson.

Each finished batch appends one record to `dashboard/launches.json`. The record has the model, the task, the minutes from launch to return, the R line count, the matched line count, the function count, the matched function count, and the return time. R lines are `count_r_lines` in `dashboard/build.py`, a count of that function's body in the package tarball. A failed proof keeps the minutes and the R lines and sets the matched lines to zero. The weight is `gpt-5.6-luna-medium` 1, `gpt-5.6-luna` 1, `claude-haiku-5-5` 1, `claude-haiku-5-5-thinking-high` 2, `composer-2.5-fast` 2, `grok-4.7-high-fast` 3, `gpt-5.6-sol-medium` 4, `gemini-4-argon-medium` 5, `claude-sonnet-5-5-high` 9, `claude-opus-5-5-medium` 17. R lines per minute is speed. Success is the matched function count divided by the function count. Yield is matched R lines divided by weight times minutes.

The orchestrator reads `dashboard/launches.json` for the next model, not the home page. Run `python3 dashboard/build.py --cost-advice` to see which models are set aside. A missing experience filename is why Luna ran on work that later needs thinking Haiku. The one lesson the agent already wrote is the filename the next match uses, so the next model is `claude-haiku-5-5-thinking-high` when the launcher accepts that slug, and otherwise `gpt-5.6-luna-medium`. A filename that matched and still took a long time gets one added sentence in that same file. A strategy file is edited only when later batches that already matched a filename stay below the stored pace. The pace is matched lines divided by weight times minutes, the same number the curve plots. A new strategy file is added only when no name under `strategies/` describes that cheaper path, and the constitution's strategy list gains that name in the same edit. No agent is started to rewrite the instructions.

A model is set aside for a task when that model has at least five finished batches of the task and a cheaper model listed for that same task has the higher yield on it. `python-numerical` may also be `gpt-5.6-luna-medium`. `python-other` may also be `gpt-5.6-luna-medium`. `python-match` may also be `gpt-5.6-luna-medium`. A new crate is `claude-haiku-5-5-thinking-high`. A proof that failed once is retried on `claude-haiku-5-5-thinking-high`, once, then stop. The first-match line wins when no cheaper model listed for that task has a higher yield.
