`daspk` needs `ddaspk.f`, `opkda1.f`, `errmsg.f`, `dlinpk.f`, and `daux.f`.
`lsode` calls `dlsode_` from `opkdmain.f` with `liw` 20 or `20+n`, not VODE's 30. `saveOut` uses `iin=c(1,12:19)` and `iout=c(1:3,14,5:9)`.
`lsodes` adds `dsparsk.f` and `dlsoder.f`. `errmsg.f` already defines `rprintd*`. `ode.2D` and `ode.3D` build sparsity in the Python driver because `lsodes` still rejects `sparsetype` 2D and 3D.
`lsodar` needs `errmsg.f` and `dlinpk.f`, and must guard `iwork[9+k]` when `liw` is only `20+n`.
`vode` writes `hini`, `hmax`, and `hmin` at `rwork[4:6]` and `maxord` / `maxsteps` at `iwork[4:5]` before `dvode`.
`dvode` band `lrw` must use the real `banddown` and `bandup`. Hard-coding 1 makes banded `ode.1D` return `istate=-3` when `nspec` is 2.
`zvode` must read `real` and `imag` before an `f64` extract, or a complex value becomes a zero derivative.
`radau` dense output needs its own `ytmp`.
`rk` default `rk45dp7` needs `densetype` 1 in `crates/rksolv`, Fortran-order `A`, and `istate[11:15]` mapped through `c(1,12:15)` to `c(1:3,13,18)`.
`dede` default `lsoda` uses `itask=5` and updates history after every accept. `lagvalue` reads only the first element of `t`. `lagderiv` is `past(..., val=2)`.
`ccl4model` is `init_ccl4` / `derivs_ccl4`. `DLLfunc` maps `aquaphy` and `derivsccl4` onto those crates.
`lsoda` calls `dlsoda_` with `liw = 20+n` and `lrw = max(lrn, lrs)`, where `lrn = 20+n*(maxordn+1)+3*n` and `lrs` adds the Jacobian block. `iwork[8]` and `iwork[9]` hold `maxordn` and `maxords` only when they differ from 12 and 5. `saveOut` uses `iin=c(1,12:21)` and `iout=c(1:3,14,5:9,15:16)`.
