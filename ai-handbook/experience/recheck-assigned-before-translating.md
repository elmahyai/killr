# Recheck assigned before translating

The doable list is read once at the start of a run. The owning session can write `assigned` on every untranslated function of a package while a sub-agent is still working. In locfit, all 40 untranslated functions gained one agent id about one minute after the run began, so the list that was doable at start became empty.

Re-read `translation.json` right before any code is written and before each function is started. Treat any non-empty `assigned` as owned by another agent and do not translate it. If the id is your own launch claim, the parent must confirm that before you proceed.

Also check `not_done`. A function can have an empty `blocked_by` while its `not_done` says `Waiting on ...`, for example `density.lf` and `gam.lf` in locfit that wait on the crate. Treat that text as a wait until the record is corrected.
