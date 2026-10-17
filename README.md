<p align="center">
  <img src="docs/assets/logo.jpg" width="420" alt="killr: Rust and Python, the AI-powered R replacement">
</p>
<p align="center"><b><a href="https://elmahyai.github.io/killr/">Live dashboard: elmahyai.github.io/killr</a></b></p>


# killr

**Kill CRAN.** killr is an agent system that translates the R package catalog (CRAN) into Python and Rust, and proves every translated function against R.

- Front page with the live dashboard: [docs/index.html](docs/index.html) (published on GitHub Pages once enabled)
- How the system works, with a graph: [docs/strategy.md](docs/strategy.md)
- What is still open: [docs/roadmap.md](docs/roadmap.md)

## Layout

| Path | What it holds |
| --- | --- |
| `CONSTITUTION.md` | The rules for translating a package |
| `strategies/` | One strategy per package size, plus the orchestrator |
| `experience/` | Lessons learned by the agents, one file per pitfall |
| `packages/<Name>/` | One translated R package: Python code, proofs, outputs |
| `crates/<name>/` | Rust kernels for Fortran and C that compute |
| `killplot/` | The shared plotting helpers |
| `registry.json` | The generated record of every package, crate, and native library |
| `dashboard/` | The build script and the dashboard pages |
| `docs/` | The front page, logo, strategy and roadmap documents |

## Rebuild the registry and dashboard

```bash
python3 dashboard/build.py --home
```

The `cran/` folder is excluded from git. It holds the CRAN catalog, the download ranking, the replaced-package list, and the downloaded R tarballs (`cran/contrib/`). A clone without it still builds, but the CRAN ranking and the replaced-package list come out empty until that folder is restored.

<!-- progress:start -->

## Progress

Snapshot from the registry, 2026-10-17 21:34 UTC. The interactive version is at [https://elmahyai.github.io/killr/](https://elmahyai.github.io/killr/).

![complete](https://img.shields.io/badge/complete-133-brightgreen) ![in progress](https://img.shields.io/badge/in%20progress-17-yellow) ![replaced](https://img.shields.io/badge/replaced-38-lightgrey) ![functions](https://img.shields.io/badge/functions-6099%20of%206608-blue) ![proof checks](https://img.shields.io/badge/proof%20checks-6544%20of%206590-blue) ![rust crates](https://img.shields.io/badge/rust%20crates-132-orange)

| Status | Packages |
| --- | ---: |
| Complete | 133 |
| In progress | 17 |
| Replaced by a stand-in | 38 |

<details>
<summary>All 188 packages (grade A to F; EX is exempt)</summary>

| Package | Status | Grade | Functions | Proof checks | Median speedup |
| --- | --- | :---: | ---: | ---: | ---: |
| abind | complete | A | 5 / 5 | 5 / 5 | 1.4x |
| askpass | complete | A | 2 / 2 | 2 / 2 | 111.63x |
| assertthat | complete | A | 26 / 26 | 26 / 26 | 2.75x |
| backports | complete | A | 47 / 47 | 47 / 47 | 10.92x |
| base64enc | complete | A | 4 / 4 | 4 / 4 | 0.36x |
| BB | complete | A | 7 / 7 | 7 / 7 | 1.84x |
| blob | complete | A | 8 / 8 | 8 / 8 | 69.19x |
| boot | complete | B | 93 / 93 | 42 / 43 | 2.39x |
| brio | complete | A | 9 / 9 | 9 / 9 | 1.64x |
| ca | complete | A | 10 / 10 | 10 / 10 | 3.66x |
| changepoint | complete | A | 54 / 54 | 49 / 49 | 0.35x |
| checkmate | complete | A | 370 / 370 | 370 / 370 | 1.43x |
| class | complete | A | 15 / 15 | 15 / 15 | 0.65x |
| cli | complete | A | 240 / 240 | 240 / 240 | 11.01x |
| clipr | complete | A | 7 / 7 | 7 / 7 | 2.11x |
| cluster | complete | A | 25 / 25 | 25 / 25 | 1.33x |
| coda | complete | A | 48 / 48 | 48 / 48 | 1.5x |
| collapse | complete | A | 384 / 384 | 382 / 382 | 0.42x |
| colorspace | complete | C | 52 / 92 | 52 / 52 | 3.87x |
| conflicted | complete | A | 5 / 5 | 5 / 5 | - |
| corpcor | complete | A | 29 / 29 | 29 / 29 | 1.76x |
| crayon | complete | A | 46 / 46 | 46 / 46 | 25.23x |
| curl | replaced | EX | 37 / 44 | 26 / 37 | 0.66x |
| data.table | replaced | EX | 54 / 141 | 54 / 54 | 0.79x |
| deldir | in progress | F | 0 / 2 | 0 / 0 | - |
| DEoptimR | complete | A | 3 / 3 | 3 / 3 | 3.33x |
| deSolve | complete | A | 37 / 37 | 37 / 37 | 1.22x |
| diffobj | complete | A | 60 / 60 | 60 / 60 | 8.52x |
| digest | complete | A | 9 / 9 | 9 / 9 | 1.5x |
| doParallel | replaced | EX | 0 / 2 | 0 / 0 | - |
| dplyr | replaced | EX | 2 / 284 | 2 / 2 | 0.02x |
| e1071 | complete | A | 62 / 62 | 62 / 62 | 4.19x |
| ellipse | complete | A | 4 / 4 | 4 / 4 | 0.57x |
| estimability | complete | A | 8 / 8 | 8 / 8 | 5.94x |
| evaluate | complete | A | 17 / 17 | 17 / 17 | 14.28x |
| exactextractr | complete | A | 4 / 4 | 4 / 4 | 26.01x |
| extraDistr | complete | A | 194 / 194 | 194 / 194 | 0.23x |
| fansi | complete | A | 44 / 44 | 44 / 44 | 0.77x |
| farver | complete | A | 13 / 13 | 13 / 13 | 1.18x |
| fastmap | complete | A | 5 / 5 | 5 / 5 | 7.92x |
| fastmatch | complete | A | 6 / 6 | 6 / 6 | 1.31x |
| filelock | complete | A | 2 / 2 | 2 / 2 | 4.33x |
| fitdistrplus | in progress | D | 1 / 27 | 1 / 1 | 17.55x |
| FNN | complete | A | 17 / 17 | 17 / 17 | 0.25x |
| fontawesome | complete | B | 4 / 5 | 4 / 4 | 30.18x |
| foreach | replaced | EX | 0 / 23 | 0 / 0 | - |
| Formula | complete | A | 4 / 4 | 4 / 4 | 18.19x |
| fracdiff | complete | A | 7 / 7 | 7 / 7 | 0.35x |
| fs | complete | A | 69 / 69 | 69 / 69 | 4.91x |
| generics | replaced | EX | 23 / 39 | 23 / 23 | 0.99x |
| ggplot2 | replaced | EX | 5 / 643 | 5 / 5 | 0.93x |
| glue | complete | A | 16 / 16 | 16 / 16 | 7.64x |
| goftest | complete | A | 7 / 7 | 7 / 7 | 3.01x |
| gower | complete | A | 2 / 2 | 2 / 2 | 2.04x |
| GPArotation | complete | A | 42 / 42 | 42 / 42 | 1.05x |
| gridExtra | replaced | EX | 0 / 16 | 0 / 0 | - |
| gtools | in progress | C | 35 / 47 | 35 / 35 | 2.05x |
| haven | complete | A | 28 / 28 | 28 / 28 | 6.96x |
| hexbin | complete | C | 27 / 46 | 27 / 27 | 4.21x |
| htmlTable | in progress | F | 0 / 24 | 0 / 0 | - |
| htmltools | replaced | EX | 4 / 77 | 4 / 4 | 17.97x |
| httr | replaced | EX | 5 / 91 | 5 / 5 | 8.56x |
| httr2 | replaced | EX | 4 / 155 | 4 / 4 | 1.17x |
| igraph | replaced | EX | 3 / 841 | 3 / 3 | 1561.02x |
| ineq | complete | A | 32 / 32 | 31 / 31 | 1.12x |
| interp | in progress | A | 7 / 7 | 7 / 7 | 0.82x |
| isoband | complete | B | 12 / 16 | 12 / 12 | 6.01x |
| iterators | replaced | EX | 6 / 16 | 6 / 6 | 4.69x |
| janitor | in progress | F | 0 / 39 | 0 / 0 | - |
| jquerylib | complete | A | 1 / 1 | 1 / 1 | 70.56x |
| jsonlite | complete | A | 23 / 23 | 23 / 23 | 10.72x |
| KernSmooth | complete | A | 7 / 7 | 7 / 7 | 1.02x |
| knitr | replaced | EX | 6 / 133 | 6 / 6 | 4.55x |
| labeling | complete | A | 10 / 10 | 10 / 10 | 0.06x |
| labelled | in progress | F | 0 / 54 | 0 / 0 | - |
| lattice | replaced | EX | 24 / 147 | 24 / 24 | 8.34x |
| leaps | complete | A | 2 / 2 | 2 / 2 | 0.39x |
| lifecycle | complete | A | 16 / 16 | 16 / 16 | 49.68x |
| listenv | complete | A | 8 / 8 | 8 / 8 | 11.41x |
| lmom | complete | A | 67 / 67 | 67 / 67 | 1.3x |
| lmtest | complete | A | 23 / 23 | 23 / 23 | 4.21x |
| locfit | complete | B | 43 / 53 | 43 / 43 | 1.34x |
| logspline | in progress | F | 0 / 22 | 0 / 0 | - |
| lubridate | complete | A | 159 / 159 | 159 / 159 | 7.63x |
| magrittr | complete | A | 42 / 42 | 42 / 42 | 1.53x |
| MASS | complete | A | 164 / 164 | 163 / 163 | 2.35x |
| mathjaxr | complete | A | 1 / 1 | 1 / 1 | 50.52x |
| Matrix | in progress | F | 0 / 1 | 0 / 0 | - |
| matrixcalc | complete | A | 60 / 60 | 60 / 60 | 1.95x |
| matrixStats | complete | A | 102 / 102 | 102 / 102 | 1.37x |
| mclust | complete | B | 281 / 285 | 280 / 281 | 1.65x |
| memoise | complete | A | 12 / 12 | 12 / 12 | 3.84x |
| Metrics | complete | A | 32 / 32 | 32 / 32 | 1.31x |
| mime | complete | A | 3 / 3 | 3 / 3 | 18.75x |
| minpack.lm | complete | A | 4 / 4 | 4 / 4 | 1.7x |
| minqa | complete | A | 3 / 3 | 3 / 3 | 1.34x |
| mitools | complete | A | 4 / 4 | 4 / 4 | 5.82x |
| mix | complete | A | 14 / 14 | 14 / 14 | 0.7x |
| modelr | complete | A | 39 / 39 | 34 / 34 | 7.32x |
| modeltools | complete | A | 19 / 19 | 19 / 19 | 146.9x |
| moments | complete | A | 12 / 12 | 12 / 12 | 0.94x |
| mvtnorm | complete | A | 61 / 61 | 61 / 61 | 1.69x |
| nlme | in progress | B | 106 / 109 | 105 / 105 | 4.84x |
| nloptr | complete | A | 26 / 26 | 26 / 26 | 1.79x |
| nnet | complete | A | 7 / 7 | 7 / 7 | 0.24x |
| nortest | complete | A | 5 / 5 | 5 / 5 | 2.61x |
| numDeriv | complete | A | 4 / 4 | 4 / 4 | 0.74x |
| openssl | replaced | EX | 46 / 79 | 40 / 46 | 16.53x |
| ordinal | in progress | B | 23 / 28 | 23 / 23 | 1.93x |
| otel | complete | A | 39 / 39 | 39 / 39 | - |
| pan | complete | A | 5 / 5 | 5 / 5 | 0.79x |
| pbapply | replaced | EX | 17 / 26 | 17 / 17 | 12.78x |
| pbivnorm | complete | A | 1 / 1 | 1 / 1 | 0.97x |
| permute | complete | A | 52 / 52 | 52 / 52 | 34.62x |
| pillar | replaced | EX | 44 / 46 | 44 / 44 | 13.65x |
| pkgconfig | complete | F | 0 / 3 | 0 / 0 | - |
| plyr | replaced | EX | 4 / 75 | 4 / 4 | 0.06x |
| png | complete | A | 2 / 2 | 2 / 2 | 0.48x |
| polynom | complete | A | 21 / 21 | 21 / 21 | 5.38x |
| pracma | complete | A | 456 / 456 | 454 / 454 | 0.44x |
| prettyunits | complete | A | 14 / 14 | 14 / 14 | 4.93x |
| progressr | complete | A | 34 / 34 | 34 / 34 | 0.32x |
| proxy | complete | A | 14 / 14 | 14 / 14 | 27.3x |
| purrr | replaced | EX | 3 / 184 | 3 / 3 | 0.14x |
| pwr | complete | A | 15 / 15 | 15 / 15 | 0.67x |
| quadprog | complete | A | 2 / 2 | 2 / 2 | 0.18x |
| quantmod | in progress | F | 0 / 1 | 0 / 0 | - |
| quantreg | in progress | B | 129 / 154 | 113 / 113 | 1.1x |
| R6 | replaced | EX | 0 / 3 | 0 / 0 | - |
| randomForest | complete | A | 18 / 18 | 18 / 18 | 0.62x |
| rappdirs | complete | A | 7 / 7 | 7 / 7 | 21.96x |
| RColorBrewer | complete | A | 4 / 4 | 4 / 4 | 5.52x |
| Rdpack | replaced | EX | 0 / 110 | 0 / 0 | - |
| readr | complete | A | 103 / 103 | 103 / 103 | 18.0x |
| readxl | replaced | EX | 9 / 13 | 9 / 9 | 29.83x |
| reformulas | in progress | F | 0 / 32 | 0 / 0 | - |
| rematch2 | complete | A | 8 / 8 | 8 / 8 | 18.23x |
| remotes | complete | A | 38 / 38 | 38 / 38 | 15.88x |
| reshape2 | replaced | EX | 3 / 6 | 3 / 3 | 0.08x |
| RJSONIO | complete | A | 24 / 24 | 24 / 24 | 20.49x |
| rlang | replaced | EX | 59 / 447 | 43 / 59 | 9.29x |
| rootSolve | complete | A | 20 / 20 | 20 / 20 | 0.43x |
| rpart | complete | A | 14 / 14 | 14 / 14 | 1.03x |
| rprojroot | replaced | EX | 0 / 37 | 0 / 0 | - |
| rstudioapi | replaced | EX | 3 / 130 | 3 / 3 | 8.54x |
| rvest | in progress | F | 0 / 38 | 0 / 0 | - |
| sandwich | complete | A | 37 / 37 | 33 / 33 | 6.35x |
| sass | complete | B | 22 / 28 | 22 / 22 | 15.86x |
| scales | replaced | EX | 6 / 213 | 6 / 6 | 1.73x |
| sf | replaced | EX | 4 / 157 | 4 / 4 | 3.48x |
| shiny | replaced | EX | 5 / 284 | 5 / 5 | 12.46x |
| simpleboot | complete | B | 18 / 18 | 15 / 18 | 2.79x |
| slam | complete | A | 33 / 33 | 33 / 33 | 0.42x |
| slider | in progress | B | 83 / 101 | 83 / 83 | 3.55x |
| snakecase | complete | B | 12 / 13 | 12 / 12 | 23.56x |
| SQUAREM | complete | A | 2 / 2 | 2 / 2 | 0.66x |
| statmod | complete | A | 50 / 50 | 50 / 50 | 0.93x |
| stringdist | complete | A | 19 / 19 | 19 / 19 | 0.81x |
| stringi | complete | A | 256 / 256 | 256 / 256 | 0.22x |
| stringr | complete | A | 66 / 66 | 63 / 63 | 0.76x |
| survival | complete | C | 78 / 136 | 77 / 78 | 2.14x |
| sys | complete | A | 11 / 11 | 11 / 11 | 4.89x |
| testthat | complete | A | 207 / 207 | 207 / 207 | 225.57x |
| tibble | replaced | EX | 4 / 45 | 4 / 4 | 18.67x |
| tidyr | replaced | EX | 1 / 70 | 1 / 1 | 0.65x |
| tidyselect | replaced | EX | 6 / 29 | 6 / 6 | 0.48x |
| timechange | complete | A | 10 / 10 | 10 / 10 | 0.91x |
| tools | replaced | EX | 68 / 136 | 68 / 68 | 13.16x |
| truncnorm | complete | A | 6 / 6 | 6 / 6 | 0.2x |
| tseries | in progress | B | 43 / 44 | 43 / 43 | 2.72x |
| TTR | complete | A | 68 / 68 | 67 / 67 | 0.47x |
| tzdb | complete | A | 4 / 4 | 4 / 4 | 4.25x |
| ucminf | complete | A | 1 / 1 | 1 / 1 | 0.37x |
| urca | complete | B | 25 / 25 | 24 / 25 | 5.45x |
| utf8 | complete | A | 9 / 9 | 9 / 9 | 6.61x |
| utils | replaced | EX | 29 / 264 | 26 / 29 | 8.68x |
| vars | complete | A | 26 / 26 | 26 / 26 | 7.93x |
| vctrs | replaced | EX | 5 / 200 | 2 / 5 | 6.02x |
| viridisLite | complete | A | 10 / 10 | 10 / 10 | - |
| warp | complete | A | 3 / 3 | 3 / 3 | 0.06x |
| withr | complete | C | 57 / 79 | 57 / 57 | 6.2x |
| XML | replaced | EX | 71 / 173 | 71 / 71 | 10.34x |
| xml2 | complete | A | 67 / 67 | 67 / 67 | 1.74x |
| xmlparsedata | complete | A | 2 / 2 | 2 / 2 | 47.74x |
| xtable | replaced | EX | 22 / 29 | 22 / 22 | 30.99x |
| xts | complete | A | 113 / 113 | 113 / 113 | 7.34x |
| yaml | complete | A | 6 / 6 | 6 / 6 | 0.59x |
| zoo | complete | C | 88 / 126 | 88 / 88 | 3.62x |

</details>

<!-- progress:end -->
