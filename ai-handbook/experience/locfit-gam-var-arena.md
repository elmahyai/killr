# Locfit gam.lf var is a work-array slice

R's `gam.lf` var is not a per-observation variance. `locfit.raw(geth = 4)` returns `z$wdes[n*(p+2) + p*p + (1:n)]`, a slice of the design work array that `ressumm` leaves behind. The `des_init` layout is `X` (n*p), `w`, `res`, `di`, `th`, `wd`, `V`, ..., so the slice starts at `di` plus `p*p`.

After the orthogonal step, `di[i] = min(1, nlx_i^2 * w_i)`, `th` holds the orthogonal fit, and `wd = y - fitted`. So `var[k]` is entry `p*p + k` of the concatenation `[di, th, wd]`, with `p = choose(d + deg, deg)`. It can be negative and wraps across blocks. It is only reproducible while `p*p + n <= 3n`.
