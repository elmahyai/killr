`vec_rbind()` and `vec_cbind()` in vctrs allow two columns with the same name. `slide_dfr(x, ~ data.frame(a = .x[1], a = .x[1]), .before = 1)` stacks two columns both called `a`, and `slide_dfc(..., .name_repair = "minimal")` keeps every generated name as it is, duplicates included. Polars rejects that shape everywhere: `pl.DataFrame`, `hstack`, `select`, `rename`, and `concat` all raise `DuplicateError`; only a lazy `alias` is tolerated, and it fails on collect.

So the binders raise `SliderError` when a repair mode leaves a repeated name, and the message names the modes that avoid it (`unique` or `universal`). Do not silently suffix the second name: R's default is already `unique`, so only an explicit `minimal` reaches that path, and inventing `a_2` would be a different result from what the caller asked for.

Every other naming rule does carry over, and these were checked case by case against R:

- `...1`, `...2`, and the rest are positional names: R treats them as unnamed and replaces them with the column position, so `dfr` gets `1`, `2`, ... rather than the literal `...1`.
- A blank name counts as unnamed the same way.
- `dfr` accepts `unique`, `universal`, and `check_unique`; it rejects `minimal`, because a row bind has to match columns by name.
- `dfc` accepts all four, `minimal` included.
- `vec_cbind()` skips a `NULL` result and keeps the other windows, so the binder drops `None` rather than making every column missing.
