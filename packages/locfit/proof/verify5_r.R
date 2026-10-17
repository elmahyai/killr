# R reference values and timings for the five-function check: hatmatrix,
# kappa0, kdeb, lcv, and lf.
#
# Run from the repository root:
#   Rscript packages/locfit/proof/verify5_r.R
#
# Every explicit-path value comes from the real locfit 1.5-9.12 functions with
# ev = dat(), on the fixed inputs written by kernel_inputs_r.R
# (locfit_kernel_inputs.csv and locfit_kernel_dsamp.csv). R's default ev = rbox()
# (and lfgrid(20) for kappa0) needs the kd-tree, so those values are written to
# a separate default file for the record and are not compared.
#
# hatmatrix(): R's exported hatmatrix() stops with "data is too long" on every
# form tried (formula, ev = dat(); formula, default ev; numeric x, y). Its body
# asks locfit(..., geth = 1) for the local operator and reshapes it. The
# reference used here is that same operator, locfit.raw(..., geth = 1, ev = dat()),
# transposed. locfit.raw returns the operator with column sums 1; the hat matrix
# H satisfies H %*% y = fitted, which is checked below (t(raw) is H).
#
# Timing: one untimed call, then the median of 20 samples. Each sample is a loop
# of K calls; the reported time is the sample time divided by K. Sys.time().

lib <- Sys.getenv("LOCFIT_RLIB", unset = "/tmp/locfit-rlib")
library(locfit, lib.loc = lib)

out <- "packages/locfit/docs/output"
dir.create(out, recursive = TRUE, showWarnings = FALSE)

inp <- read.csv(file.path(out, "locfit_kernel_inputs.csv"))
x <- inp$x
y <- inp$y
dsamp <- read.csv(file.path(out, "locfit_kernel_dsamp.csv"))$dsamp
xm <- matrix(x, ncol = 1)

K <- 20L

# Each closure is one case. kappa0 prints a C-level note on every call;
# capture.output keeps the log clean without changing the value.
hatmatrix_raw <- function() t(locfit.raw(xm, y, ev = dat(), geth = 1))

kappa0_dat <- function() {
  v <- NULL
  capture.output(v <- suppressWarnings(
    kappa0(y ~ x, cov = 0.95, ev = dat())$crit.val))
  v
}

kdeb_dsamp <- function() kdeb(dsamp)

lcv_dat <- function() lcv(x, y, ev = dat())

lf_dat <- function() lf(x, y, alpha = 0.5, deg = 1, scale = 2,
                        kern = "gauss", maxk = 50, ev = dat())

fmt <- function(v) paste(sprintf("%.17g", as.numeric(v)), collapse = ",")

# Values, row-major for matrices (so Python reshapes in C order).
ref_hat <- hatmatrix_raw()
lf_obj <- lf_dat()
values <- c(
  hatmatrix_raw = fmt(t(ref_hat)),
  kappa0_dat = fmt(kappa0_dat()),
  kdeb_dsamp = fmt(kdeb_dsamp()),
  lcv_dat = fmt(lcv_dat()[c("lik", "infl", "vari", "cv")]),
  lf_x = fmt(t(lf_obj)),
  lf_num = fmt(c(attr(lf_obj, "alpha"), attr(lf_obj, "deg"),
                 attr(lf_obj, "scale"), attr(lf_obj, "maxk")))
)
writeLines(paste(names(values), values, sep = ","),
           file.path(out, "locfit_verify5_r_values.txt"))

strings <- c(
  kdeb_names = paste(names(kdeb_dsamp()), collapse = "|"),
  lf_kern = attr(lf_obj, "kern"),
  lf_ev_type = attr(lf_obj, "ev")$type,
  lf_class = class(lf_obj)[1]
)
writeLines(paste(names(strings), strings, sep = ","),
           file.path(out, "locfit_verify5_r_strings.txt"))

time_call <- function(f) {
  f()
  samples <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- Sys.time()
    for (j in seq_len(K)) f()
    samples[i] <- as.numeric(Sys.time() - t0) * 1000
  }
  median(samples) / K
}

timing <- c(
  hatmatrix_raw = time_call(hatmatrix_raw),
  kappa0_dat = time_call(kappa0_dat),
  kdeb_dsamp = time_call(kdeb_dsamp),
  lcv_dat = time_call(lcv_dat),
  lf_dat = time_call(lf_dat)
)
writeLines(sprintf("%s,%.17g", names(timing), timing),
           file.path(out, "locfit_verify5_r_timing.txt"))

# Default-path facts for the record (not compared).
hat_default <- try(hatmatrix(y ~ x), silent = TRUE)
hat_dat <- try(hatmatrix(y ~ x, ev = dat()), silent = TRUE)
kappa0_default <- suppressWarnings(capture.output(
  k0 <- kappa0(y ~ x, cov = 0.95)$crit.val))
hat_fit_gap <- max(abs(ref_hat %*% y -
  fitted(locfit.raw(xm, y, ev = dat()))))
default_lines <- c(
  sprintf("hatmatrix_H_times_y_minus_fitted_max,%.17g", hat_fit_gap),
  paste0("hatmatrix_formula_dat_error,",
         gsub(",", ";", trimws(as.character(hat_dat)))),
  paste0("hatmatrix_formula_default_error,",
         gsub(",", ";", trimws(as.character(hat_default)))),
  sprintf("kappa0_default_lfgrid20_crit_val,%.17g", k0),
  paste0("lf_default_ev_type,", attr(lf(x, y), "ev")$type),
  paste0("lf_default_ev_cut,", attr(lf(x, y), "ev")$cut)
)
writeLines(default_lines, file.path(out, "locfit_verify5_r_default.txt"))

print(values)
print(strings)
print(timing)
print(default_lines)
