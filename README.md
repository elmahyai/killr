<p align="center">
  <img src="docs/assets/logo.jpg" width="420" alt="killr: Rust and Python, the AI-powered R replacement">
</p>

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
