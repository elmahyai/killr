# Proof (R side): reference fits from the R function locfit.raw in locfit 1.5-9.12.
#
# Source: cran/contrib/locfit_1.5-9.12.tar.gz. Install it once into a library:
#   R CMD INSTALL --library=/tmp/locfit-rlib cran/contrib/locfit_1.5-9.12.tar.gz
# Then run from the repository root:
#   LOCFIT_RLIB=/tmp/locfit-rlib Rscript packages/locfit/proof/locfit_r_proof.R
#
# Writes into packages/locfit/docs/output:
#   locfit_<case>_data.csv    shared input data (x columns, then y)
#   locfit_<case>_xev.csv     evaluation points (pres case only)
#   locfit_r_<case>_eva.csv   full eva$coef matrix from locfit.raw
#   locfit_r_<case>_dp.csv    dp summaries lk, df1, df2, rv
#   locfit_r_timing.csv       median of 20 timed calls, milliseconds
#   locfit_r_session.txt      R and package version used

lib <- Sys.getenv("LOCFIT_RLIB", unset = "")
if (nzchar(lib)) {
  suppressPackageStartupMessages(library(locfit, lib.loc = lib))
} else {
  suppressPackageStartupMessages(library(locfit))
}
stopifnot(as.character(packageVersion("locfit")) == "1.5.9.12")

out <- "packages/locfit/docs/output"
dir.create(out, recursive = TRUE, showWarnings = FALSE)

write_csv_mat <- function(m, file, header) {
  con <- file(file, "w")
  on.exit(close(con))
  writeLines(paste(header, collapse = ","), con)
  for (i in seq_len(nrow(m))) {
    writeLines(paste(sprintf("%.17g", m[i, ]), collapse = ","), con)
  }
}

set.seed(20241017)
n1 <- 500
x1 <- matrix(runif(n1), ncol = 1)
y1 <- sin(2 * pi * x1[, 1]) + rnorm(n1, sd = 0.2)
n2 <- 300
x2 <- matrix(runif(2 * n2), ncol = 2)
y2 <- sin(3 * x2[, 1]) + x2[, 2]^2 + rnorm(n2, sd = 0.1)
xev1 <- matrix(seq(0, 1, length.out = 25), ncol = 1)

cases <- list(
  list(name = "d1_sph_deg2_data", x = x1, y = y1, alpha = 0.7, deg = 2,
       kt = "sph", ev = "data"),
  list(name = "d2_prod_deg1_data", x = x2, y = y2, alpha = 0.5, deg = 1,
       kt = "prod", ev = "data"),
  list(name = "d1_sph_deg2_pres", x = x1, y = y1, alpha = 0.7, deg = 2,
       kt = "sph", ev = "pres", xev = xev1)
)

# Write the shared inputs so the Rust side reads identical numbers.
for (cs in cases) {
  d <- ncol(cs$x)
  dat <- cbind(cs$x, cs$y)
  colnames(dat) <- c(paste0("x", seq_len(d)), "y")
  write_csv_mat(dat, file.path(out, paste0("locfit_", cs$name, "_data.csv")),
                colnames(dat))
  if (cs$ev == "pres") {
    write_csv_mat(cs$xev, file.path(out, paste0("locfit_", cs$name, "_xev.csv")),
                  paste0("x", seq_len(d)))
  }
}

run_r <- function(cs) {
  # A numeric ev is the set of fitting points (locfit's "pres" evaluation).
  ev <- if (cs$ev == "data") {
    list(type = "data", xev = 0, mg = 0, cut = 0, ll = 0, ur = 0)
  } else {
    as.vector(cs$xev)
  }
  locfit.raw(cs$x, cs$y, alpha = cs$alpha, deg = cs$deg,
             kern = "tricube", kt = cs$kt, ev = ev)
}

timing <- data.frame(case = character(), median_ms = numeric(), stringsAsFactors = FALSE)

for (cs in cases) {
  z <- run_r(cs)  # untimed call, also the stored result
  el <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    run_r(cs)
    el[i] <- as.numeric(Sys.time()) - t0
  }
  timing <- rbind(timing, data.frame(case = cs$name, median_ms = median(el) * 1000))

  eva <- z$eva$coef
  write_csv_mat(eva, file.path(out, paste0("locfit_r_", cs$name, "_eva.csv")),
                paste0("c", seq_len(ncol(eva))))
  dp <- z$dp[c("lk", "df1", "df2", "rv")]
  con <- file(file.path(out, paste0("locfit_r_", cs$name, "_dp.csv")), "w")
  writeLines("key,value", con)
  writeLines(sprintf("%s,%.17g", names(dp), as.numeric(dp)), con)
  close(con)
}

write.csv(timing, file.path(out, "locfit_r_timing.csv"), row.names = FALSE)
writeLines(c(R.version.string, paste("locfit", packageVersion("locfit"))),
           file.path(out, "locfit_r_session.txt"))
print(timing)
