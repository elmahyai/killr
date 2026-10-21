<p align="center">
  <img src="docs/assets/logo.jpg" width="420" alt="killr: Rust and Python, the AI-powered R replacement">
</p>
<p align="center"><b><a href="https://elmahyai.github.io/killr/">Live dashboard: elmahyai.github.io/killr</a></b></p>


# killr

**Kill R.** R holds some of the best statistics code in the world, and it is trapped in R. killr translates the CRAN catalog into Python and Rust, and every translated function is checked against the original R output.

The live page is [elmahyai.github.io/killr](https://elmahyai.github.io/killr/). It has three views:

- **About.** How a catalog this large is tackled: repeated work becomes a program, judgment stays with the model, mistakes are written down once, and a function is finished only when a proof matches R.
- **Progress by package.** Each opened package: its R files, its Depends, and whether it is free, locked, in progress, replaced, or done. A bar shows finished and in-progress packages against the whole CRAN catalog.
- **How we handle low-level code.** Fortran, C, and C++ that compute become Rust crates. A thin wrap around a system that already exists is routed, not rewritten.

The same account, with the graph, is in [docs/strategy.md](docs/strategy.md). The next rounds are in [docs/roadmap.md](docs/roadmap.md): finish the first pass, review again, raise Rust coverage, and integrate into frameworks that already exist.

## Layout

| Path | What it holds |
| --- | --- |
| `orchestrator/` | Screen, ingest, batch, prepare, and the dashboard rebuild |
| `ai-handbook/` | Constitution, strategies, experience, and native libraries |
| `rcran/` | Original CRAN tarballs, catalog, and replaced list |
| `packages/<Name>/` | One translated R package: Python code, proofs, outputs |
| `packages/killplot/` | Shared plotting helpers (a first-party package) |
| `crates/<name>/` | Rust kernels for Fortran and C that compute |
| `registry.json` | The generated record of every package, crate, and native library |
| `dashboard/` | The build script and the per-package pages |
| `docs/` | The public page, logo, strategy, and roadmap |

## Rebuild the registry and dashboard

```bash
python3 orchestrator/killr.py site
```

The `rcran/` folder is excluded from git. It holds the CRAN catalog, the download ranking, the replaced-package list, and the downloaded R tarballs (`rcran/contrib/`). A clone without it still builds, but the CRAN ranking and the replaced-package list come out empty until that folder is restored.

<!-- progress:start -->

## Progress

Snapshot from the orchestrator, 2026-10-21 06:27 UTC. The interactive version is at [https://elmahyai.github.io/killr/](https://elmahyai.github.io/killr/).

![complete](https://img.shields.io/badge/complete-135-brightgreen) ![in progress](https://img.shields.io/badge/in%20progress-14-yellow) ![replaced](https://img.shields.io/badge/replaced-39-lightgrey) ![functions](https://img.shields.io/badge/functions-6123%20of%206607-blue) ![proof checks](https://img.shields.io/badge/proof%20checks-6562%20of%206615-blue) ![close, not exact](https://img.shields.io/badge/close,%20not%20exact-7-orange) ![rust crates](https://img.shields.io/badge/rust%20crates-133-orange)

| Status | Packages |
| --- | ---: |
| Complete | 135 |
| In progress | 14 |
| Replaced by a stand-in | 39 |

<details>
<summary>All 188 packages</summary>

| Package | Status | Functions | Proof checks | Median speedup |
| --- | --- | ---: | ---: | ---: |
| BB | complete | 7 / 7 | 7 / 7 | 1.84x |
| DEoptimR | complete | 3 / 3 | 3 / 3 | 3.33x |
| FNN | complete | 17 / 17 | 17 / 17 | 0.25x |
| Formula | complete | 4 / 4 | 4 / 4 | 18.2x |
| GPArotation | complete | 42 / 42 | 42 / 42 | 1.05x |
| KernSmooth | complete | 7 / 7 | 7 / 7 | 1.02x |
| MASS | complete | 164 / 164 | 163 / 163 | 2.49x |
| Matrix | replaced | 0 / 1 | 0 / 0 | - |
| Metrics | complete | 32 / 32 | 32 / 32 | 1.31x |
| R6 | replaced | 0 / 3 | 0 / 0 | - |
| RColorBrewer | complete | 4 / 4 | 4 / 4 | 5.52x |
| RJSONIO | complete | 24 / 24 | 24 / 24 | 20.49x |
| Rdpack | replaced | 0 / 110 | 0 / 0 | - |
| SQUAREM | complete | 2 / 2 | 2 / 2 | 0.66x |
| TTR | complete | 68 / 68 | 67 / 67 | 0.47x |
| XML | replaced | 71 / 173 | 71 / 71 | 10.34x |
| abind | complete | 5 / 5 | 5 / 5 | 1.4x |
| askpass | complete | 2 / 2 | 2 / 2 | 111.62x |
| assertthat | complete | 26 / 26 | 26 / 26 | 2.75x |
| backports | complete | 47 / 47 | 47 / 47 | 10.92x |
| base64enc | complete | 4 / 4 | 4 / 4 | 0.54x |
| blob | complete | 8 / 8 | 8 / 8 | 69.19x |
| boot | complete | 93 / 93 | 42 / 43 | 2.39x |
| brio | complete | 9 / 9 | 9 / 9 | 1.64x |
| ca | complete | 10 / 10 | 10 / 10 | 3.66x |
| changepoint | complete | 54 / 54 | 49 / 49 | 0.35x |
| checkmate | complete | 370 / 370 | 370 / 370 | 1.44x |
| class | complete | 15 / 15 | 15 / 15 | 0.65x |
| cli | complete | 240 / 240 | 240 / 240 | 11.01x |
| clipr | complete | 7 / 7 | 7 / 7 | 2.11x |
| cluster | complete | 25 / 25 | 25 / 25 | 1.33x |
| coda | complete | 48 / 48 | 48 / 48 | 1.5x |
| collapse | complete | 384 / 384 | 382 / 382 | 0.42x |
| colorspace | complete | 52 / 92 | 52 / 52 | 3.87x |
| conflicted | complete | 5 / 5 | 5 / 5 | - |
| corpcor | complete | 29 / 29 | 29 / 29 | 1.76x |
| crayon | complete | 46 / 46 | 46 / 46 | 25.23x |
| curl | replaced | 37 / 44 | 26 / 37 | 0.66x |
| data.table | replaced | 54 / 141 | 54 / 54 | 0.79x |
| deSolve | complete | 37 / 37 | 37 / 37 | 1.22x |
| deldir | in progress | 0 / 2 | 0 / 0 | - |
| diffobj | complete | 60 / 60 | 60 / 60 | 8.53x |
| digest | complete | 9 / 9 | 9 / 9 | 1.5x |
| doParallel | replaced | 0 / 2 | 0 / 0 | - |
| dplyr | replaced | 2 / 284 | 2 / 2 | 0.02x |
| e1071 | complete | 62 / 62 | 62 / 62 | 4.19x |
| ellipse | complete | 4 / 4 | 4 / 4 | 0.57x |
| estimability | complete | 8 / 8 | 8 / 8 | 5.94x |
| evaluate | complete | 17 / 17 | 17 / 17 | 14.28x |
| exactextractr | complete | 4 / 4 | 4 / 4 | 26.01x |
| extraDistr | complete | 194 / 194 | 194 / 194 | 0.23x |
| fansi | complete | 44 / 44 | 44 / 44 | 0.77x |
| farver | complete | 13 / 13 | 13 / 13 | 1.18x |
| fastmap | complete | 5 / 5 | 5 / 5 | 7.92x |
| fastmatch | complete | 6 / 6 | 6 / 6 | 1.31x |
| filelock | complete | 2 / 2 | 2 / 2 | 4.33x |
| fitdistrplus | in progress | 1 / 27 | 1 / 1 | 17.55x |
| fontawesome | complete | 4 / 5 | 4 / 4 | 30.18x |
| foreach | replaced | 0 / 23 | 0 / 0 | - |
| fracdiff | complete | 7 / 7 | 7 / 7 | 0.35x |
| fs | complete | 69 / 69 | 69 / 69 | 4.91x |
| generics | replaced | 23 / 39 | 23 / 23 | 0.99x |
| ggplot2 | replaced | 5 / 643 | 5 / 5 | 0.93x |
| glue | complete | 16 / 16 | 16 / 16 | 7.63x |
| goftest | complete | 7 / 7 | 7 / 7 | 3.01x |
| gower | complete | 2 / 2 | 2 / 2 | 2.04x |
| gridExtra | replaced | 0 / 16 | 0 / 0 | - |
| gtools | in progress | 35 / 47 | 35 / 35 | 2.05x |
| haven | complete | 28 / 28 | 28 / 28 | 6.96x |
| hexbin | complete | 27 / 46 | 27 / 27 | 4.21x |
| htmlTable | in progress | 0 / 24 | 0 / 0 | - |
| htmltools | replaced | 4 / 77 | 4 / 4 | 17.97x |
| httr | replaced | 5 / 91 | 5 / 5 | 8.56x |
| httr2 | replaced | 4 / 155 | 4 / 4 | 1.17x |
| igraph | replaced | 3 / 841 | 3 / 3 | 1561.02x |
| ineq | complete | 32 / 32 | 31 / 31 | 1.12x |
| interp | in progress | 7 / 7 | 7 / 7 | 0.82x |
| isoband | complete | 12 / 16 | 12 / 12 | 6.01x |
| iterators | replaced | 6 / 16 | 6 / 6 | 4.7x |
| janitor | in progress | 0 / 39 | 0 / 0 | - |
| jquerylib | complete | 1 / 1 | 1 / 1 | 70.56x |
| jsonlite | complete | 23 / 23 | 23 / 23 | 10.72x |
| knitr | replaced | 6 / 133 | 6 / 6 | 4.54x |
| labeling | complete | 10 / 10 | 10 / 10 | 0.06x |
| labelled | in progress | 0 / 54 | 0 / 0 | - |
| lattice | replaced | 24 / 147 | 24 / 24 | 8.34x |
| leaps | complete | 2 / 2 | 2 / 2 | 0.39x |
| lifecycle | complete | 16 / 16 | 16 / 16 | 49.69x |
| listenv | complete | 8 / 8 | 8 / 8 | 11.41x |
| lmom | complete | 67 / 67 | 67 / 67 | 2.66x |
| lmtest | complete | 23 / 23 | 23 / 23 | 4.21x |
| locfit | complete | 43 / 53 | 43 / 43 | 1.34x |
| logspline | in progress | 0 / 22 | 0 / 0 | - |
| lubridate | complete | 159 / 159 | 159 / 159 | 7.63x |
| magrittr | complete | 42 / 42 | 42 / 42 | 1.53x |
| mathjaxr | complete | 1 / 1 | 1 / 1 | 50.52x |
| matrixStats | complete | 102 / 102 | 102 / 102 | 1.37x |
| matrixcalc | complete | 60 / 60 | 60 / 60 | 1.95x |
| mclust | complete | 281 / 285 | 280 / 281 | 1.65x |
| memoise | complete | 12 / 12 | 12 / 12 | 3.83x |
| mime | complete | 3 / 3 | 3 / 3 | 18.75x |
| minpack.lm | complete | 4 / 4 | 4 / 4 | 1.7x |
| minqa | complete | 3 / 3 | 3 / 3 | 1.34x |
| mitools | complete | 4 / 4 | 4 / 4 | 5.81x |
| mix | complete | 14 / 14 | 14 / 14 | 0.7x |
| modelr | complete | 39 / 39 | 34 / 34 | 7.31x |
| modeltools | complete | 19 / 19 | 19 / 19 | 146.9x |
| moments | complete | 12 / 12 | 12 / 12 | 0.94x |
| mvtnorm | complete | 61 / 61 | 61 / 61 | 1.69x |
| nlme | complete | 109 / 109 | 108 / 109 (+1 close) | 4.74x |
| nloptr | complete | 26 / 26 | 26 / 26 | 1.79x |
| nnet | complete | 7 / 7 | 7 / 7 | 0.24x |
| nortest | complete | 5 / 5 | 5 / 5 | 2.61x |
| numDeriv | complete | 4 / 4 | 4 / 4 | 0.74x |
| openssl | replaced | 46 / 79 | 40 / 46 | 16.53x |
| ordinal | in progress | 26 / 28 | 26 / 26 | 1.69x |
| otel | complete | 39 / 39 | 39 / 39 | - |
| pan | complete | 5 / 5 | 5 / 5 | 0.79x |
| pbapply | replaced | 17 / 26 | 17 / 17 | 12.78x |
| pbivnorm | complete | 1 / 1 | 1 / 1 | 0.97x |
| permute | complete | 52 / 52 | 52 / 52 | 34.62x |
| pillar | replaced | 44 / 46 | 44 / 44 | 13.65x |
| pkgconfig | complete | 0 / 3 | 0 / 0 | - |
| plyr | replaced | 4 / 75 | 4 / 4 | 0.07x |
| png | complete | 2 / 2 | 2 / 2 | 0.48x |
| polynom | complete | 21 / 21 | 21 / 21 | 5.38x |
| pracma | complete | 456 / 456 | 454 / 454 | 0.43x |
| prettyunits | complete | 14 / 14 | 14 / 14 | 4.93x |
| progressr | complete | 34 / 34 | 34 / 34 | 0.32x |
| proxy | complete | 14 / 14 | 14 / 14 | 27.3x |
| purrr | replaced | 3 / 184 | 3 / 3 | 0.14x |
| pwr | complete | 15 / 15 | 15 / 15 | 0.67x |
| quadprog | complete | 2 / 2 | 2 / 2 | 0.18x |
| quantmod | in progress | 0 / 1 | 0 / 0 | - |
| quantreg | in progress | 129 / 154 | 107 / 113 (+6 close) | 1.3x |
| randomForest | complete | 18 / 18 | 18 / 18 | 0.61x |
| rappdirs | complete | 7 / 7 | 7 / 7 | 21.96x |
| readr | complete | 103 / 103 | 103 / 103 | 18.0x |
| readxl | replaced | 9 / 13 | 9 / 9 | 29.83x |
| reformulas | in progress | 0 / 32 | 0 / 0 | - |
| rematch2 | complete | 8 / 8 | 8 / 8 | 18.23x |
| remotes | complete | 38 / 38 | 38 / 38 | 15.89x |
| reshape2 | replaced | 3 / 6 | 3 / 3 | 0.08x |
| rlang | replaced | 59 / 447 | 43 / 59 | 9.29x |
| rootSolve | complete | 20 / 20 | 20 / 20 | 0.43x |
| rpart | complete | 14 / 14 | 14 / 14 | 1.03x |
| rprojroot | replaced | 0 / 37 | 0 / 0 | - |
| rstudioapi | replaced | 3 / 130 | 3 / 3 | 8.54x |
| rvest | in progress | 0 / 38 | 0 / 0 | - |
| sandwich | complete | 37 / 37 | 33 / 33 | 6.35x |
| sass | complete | 22 / 28 | 22 / 22 | 15.86x |
| scales | replaced | 6 / 213 | 6 / 6 | 1.73x |
| sf | replaced | 4 / 157 | 4 / 4 | 3.48x |
| shiny | replaced | 5 / 284 | 5 / 5 | 12.46x |
| simpleboot | complete | 18 / 18 | 15 / 18 | 2.79x |
| slam | complete | 33 / 33 | 33 / 33 | 0.42x |
| slider | complete | 101 / 101 | 101 / 101 | 3.22x |
| snakecase | complete | 12 / 13 | 12 / 12 | 23.56x |
| statmod | complete | 50 / 50 | 50 / 50 | 0.94x |
| stringdist | complete | 19 / 19 | 19 / 19 | 0.81x |
| stringi | complete | 256 / 256 | 256 / 256 | 0.23x |
| stringr | complete | 66 / 66 | 63 / 63 | 0.76x |
| survival | complete | 78 / 136 | 77 / 78 | 2.14x |
| sys | complete | 11 / 11 | 11 / 11 | 4.89x |
| testthat | complete | 207 / 207 | 207 / 207 | 225.57x |
| tibble | replaced | 4 / 45 | 4 / 4 | 18.67x |
| tidyr | replaced | 1 / 70 | 1 / 1 | 0.65x |
| tidyselect | replaced | 6 / 29 | 6 / 6 | 0.47x |
| timechange | complete | 10 / 10 | 10 / 10 | 0.91x |
| tools | replaced | 68 / 136 | 68 / 68 | 13.2x |
| truncnorm | complete | 6 / 6 | 6 / 6 | 0.2x |
| tseries | in progress | 43 / 44 | 43 / 43 | 2.76x |
| tzdb | complete | 4 / 4 | 4 / 4 | 4.25x |
| ucminf | complete | 1 / 1 | 1 / 1 | 0.37x |
| urca | complete | 25 / 25 | 24 / 25 | 5.45x |
| utf8 | complete | 9 / 9 | 9 / 9 | 6.61x |
| utils | replaced | 29 / 264 | 26 / 29 | 8.68x |
| vars | complete | 26 / 26 | 26 / 26 | 7.94x |
| vctrs | replaced | 5 / 200 | 2 / 5 | 6.02x |
| viridisLite | complete | 10 / 10 | 10 / 10 | - |
| warp | complete | 3 / 3 | 3 / 3 | 0.06x |
| withr | complete | 57 / 79 | 57 / 57 | 6.2x |
| xml2 | complete | 67 / 67 | 67 / 67 | 1.74x |
| xmlparsedata | complete | 2 / 2 | 2 / 2 | 47.74x |
| xtable | replaced | 22 / 29 | 22 / 22 | 30.99x |
| xts | complete | 113 / 113 | 113 / 113 | 7.34x |
| yaml | complete | 6 / 6 | 6 / 6 | 0.59x |
| zoo | complete | 88 / 126 | 88 / 88 | 3.62x |

</details>

<!-- progress:end -->
