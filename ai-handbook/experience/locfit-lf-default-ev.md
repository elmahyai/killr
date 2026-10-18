# locfit lf default ev

Pitfall seen in locfit `lf`.

- R's `lf(...)` default is `ev = rbox()`, which is the list `type = "tree"`, `cut = 0.8`, `ll` and `ur` zero. It is not the string `"rbox"`.
- `lf` itself does no fitting, so a wrong default does not fail in `lf`. It fails later, when the term is fitted: `locfit_raw` raises `NotImplementedError` for any `ev` type other than `tree` or `data`.
- The kd-tree is built only at fit time. Prove the default through a chain: `lf(x)["ev"]` passed to `locfit_raw`, compared with R's `locfit.raw` on the same tree. The chain differs from a data-path fit by about 0.017, so it is a real check.
