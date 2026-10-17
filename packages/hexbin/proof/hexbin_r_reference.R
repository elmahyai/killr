# Proof, R side: call the hexbin 1.28.6 Fortran routines through .Fortran on
# fixed points, write their outputs as a reference, and time one representative
# call. Run from the repository root:
#   Rscript packages/hexbin/proof/hexbin_r_reference.R
# The matching Python check is packages/hexbin/proof/hexbin_rust_compare.py.

suppressPackageStartupMessages(library(hexbin))
stopifnot(as.character(packageVersion("hexbin")) == "1.28.6")

# Registered .Fortran entry points of the installed hexbin DLL (hbin, herode, hsm).
fortran_routines <- getDLLRegisteredRoutines("hexbin")$.Fortran

out_dir <- "packages/hexbin/docs/output"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

# Fixed points. The same formula is used in the Python script (exact in IEEE doubles).
n <- 20000L
k <- seq_len(n)
x <- ((k * 7919) %% 10007) / 10007 * 10 - 5
y <- ((k * 104729) %% 10009) / 10009 * 6 - 3

xbins <- 30
shape <- 1
xbnds <- range(x)
ybnds <- range(y)

# Grid dimensions, as hexbin() computes them.
jmax <- floor(xbins + 1.5001)
c1 <- 2 * floor((xbins * shape) / sqrt(3) + 1.5001)
imax <- trunc((jmax * c1 - 1) / jmax + 1)
lmax <- jmax * imax

# 1. hbin: the .Fortran call made by hexbin(), with per-point ids kept (cID = integer(n)).
call_hbin <- function() {
    .Fortran(fortran_routines$hbin,
             x = as.double(x), y = as.double(y),
             cell = integer(lmax), cnt = integer(lmax),
             xcm = double(lmax), ycm = double(lmax),
             xbins = as.double(xbins), shape = as.double(shape),
             xbnds = as.double(xbnds), ybnds = as.double(ybnds),
             dim = as.integer(c(imax, jmax)), n = as.integer(n),
             cID = integer(n))
}
bin <- call_hbin()
nc <- bin$n
hb <- hexbin(x, y, xbins = xbins, shape = shape, xbnds = xbnds, ybnds = ybnds)
stopifnot(identical(as.integer(hb@cell), bin$cell[seq_len(nc)]))
stopifnot(max(abs(hb@xcm - bin$xcm[seq_len(nc)])) == 0)

# 2. herode: inputs are the cells that erode.hexbin passes on after its cdf cut.
e <- erode(hb, cdfcut = 0.5)
in_cell <- hb@cell[e@eroded]
in_cnt <- as.integer(hb@count[e@eroded])
bdim <- as.integer(hb@dimen)
L <- bdim[1] * bdim[2]
erode_call <- .Fortran(fortran_routines$herode,
                       cell = as.integer(in_cell), cnt = in_cnt,
                       n = length(in_cell), bdim = bdim,
                       erode = integer(L), ncnt = integer(L),
                       ncell = integer(L), sides = integer(L),
                       neib = integer(6 * L), exist = logical(L + 1))$erode
erode_out <- erode_call[seq_along(in_cell)]
stopifnot(identical(as.integer(e@erode), erode_out))

# 3. hsm: the padded inputs that smooth.hexbin builds, default weights c(48, 4, 1).
wts <- c(48L, 4L, 1L)
cell0 <- hb@cell - 1
n_cells <- length(cell0)
cnt0 <- hb@count
row <- bdim[1]
col <- bdim[2]
ncol <- col + 4L
nrow <- row + 4L
nmax <- ncol * nrow
sm0 <- rep.int(0L, nmax)
nr <- cell0 %/% col + 2
nc_pad <- cell0 %% col + 3
pad <- rep.int(0L, nmax - n_cells)
hsm_cell <- c(nr * ncol + nc_pad, pad)
hsm_cnt <- c(cnt0, pad)
hsm_call <- .Fortran(fortran_routines$hsm,
                     cell = as.integer(hsm_cell), cnt = as.integer(hsm_cnt),
                     n = as.integer(n_cells), nmax = as.integer(nmax),
                     sm = as.integer(sm0), ncol = as.integer(ncol),
                     wts = wts)
hsm_n <- hsm_call$n
hsm_out_cell <- hsm_call$cell[seq_len(hsm_n)]
hsm_out_cnt <- hsm_call$cnt[seq_len(hsm_n)]
sm_obj <- hexbin:::smooth.hexbin(hb, wts = c(48, 4, 1))
stopifnot(identical(as.integer(sm_obj@cell), as.integer(hsm_out_cell)))

# Reference file: long format, one value per row, 0-based index.
fmt_int <- function(v) sprintf("%d", as.integer(v))
fmt_dbl <- function(v) sprintf("%.17g", as.numeric(v))
rows <- character(0)
add <- function(kernel, name, v, fmt) {
    if (length(v) == 0L) return(invisible(NULL))
    rows <<- c(rows, paste(kernel, name, seq_along(v) - 1L, fmt(v), sep = ","))
}
add("points", "x", x, fmt_dbl)
add("points", "y", y, fmt_dbl)
add("hbin", "dim_in", c(imax, jmax), fmt_int)
add("hbin", "n", nc, fmt_int)
add("hbin", "dim_out", bin$dim, fmt_int)
add("hbin", "cell", bin$cell[seq_len(nc)], fmt_int)
add("hbin", "cnt", bin$cnt[seq_len(nc)], fmt_int)
add("hbin", "xcm", bin$xcm[seq_len(nc)], fmt_dbl)
add("hbin", "ycm", bin$ycm[seq_len(nc)], fmt_dbl)
add("hbin", "cell_ids", bin$cID, fmt_int)
add("herode", "in_cell", in_cell, fmt_int)
add("herode", "in_cnt", in_cnt, fmt_int)
add("herode", "bdim", bdim, fmt_int)
add("herode", "erode", erode_out, fmt_int)
add("hsm", "in_cell", hsm_cell[seq_len(n_cells)], fmt_int)
add("hsm", "in_cnt", hsm_cnt[seq_len(n_cells)], fmt_int)
add("hsm", "nmax", nmax, fmt_int)
add("hsm", "ncol", ncol, fmt_int)
add("hsm", "wts", wts, fmt_int)
add("hsm", "out_cell", hsm_out_cell, fmt_int)
add("hsm", "out_cnt", hsm_out_cnt, fmt_int)
writeLines(c("kernel,name,index,value", rows),
           file.path(out_dir, "hexbin-r-reference.csv"))

# Timing: median of 20 timed calls to the hbin .Fortran routine, after one untimed call.
invisible(call_hbin())
times <- numeric(20)
for (i in seq_len(20)) {
    t0 <- Sys.time()
    call_hbin()
    times[i] <- as.numeric(Sys.time() - t0, units = "secs")
}
r_median <- median(times)
timing <- c(
    "R hexbin 1.28.6 .Fortran hbin, one representative call",
    sprintf("points=%d xbins=%g shape=%g dim=(%d,%d)", n, xbins, shape, imax, jmax),
    sprintf("R median seconds (20 timed calls, Sys.time): %.9f", r_median),
    sprintf("R timings (s): %s", paste(sprintf("%.6f", times), collapse = " "))
)
writeLines(timing, file.path(out_dir, "hexbin-r-timing.txt"))
cat(timing, sep = "\n")
cat("reference written to", file.path(out_dir, "hexbin-r-reference.csv"), "\n")
