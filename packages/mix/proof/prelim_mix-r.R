.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
if (packageDescription("mix")$Version != "1.0-13") stop("expected mix 1.0-13")

# Fixed inputs as in imputeData-r.R: short binary decimals, operators parenthesised.
case_b <- function() {
  n <- 50L
  i <- 1:n
  c1 <- (i %% 3) + 1; c1[4] <- NA
  c2 <- ((i^2) %% 2) + 1
  x1 <- ((((i * 11)) %% 37) - 18) / 4; x1[7] <- NA
  x2 <- ((((i^2) + 3) %% 31) - 15) / 16; x2[20] <- NA
  cbind(c1, c2, x1, x2)
}

case_e <- function() {
  n <- 30L
  i <- 1:n
  c1 <- (i %% 4) + 1; c1[5] <- NA
  x1 <- ((((i * 7)) %% 29) - 14) / 8; x1[2] <- NA; x1[9] <- NA
  x2 <- ((((i * i) %% 11) - 5) / 4)
  cbind(c1, x1, x2)
}

num <- function(v) {
  v <- as.numeric(v)
  v[is.na(v)] <- -999999
  v
}

fields <- c("w", "n", "p", "d", "jmp", "z", "q", "r", "rz", "rw", "nmis", "ro",
            "mdpzgrp", "mdpwgrp", "mobs", "mobsst", "nmobs", "ncells", "ngrp",
            "npattz", "npattw", "npsi", "psi", "xbar", "sdv")

one <- function() {
  b <- mix::prelim.mix(case_b(), p = 2)
  e <- mix::prelim.mix(case_e(), p = 1)
  out <- numeric(0)
  for (s in list(b, e)) for (f in fields) out <- c(out, num(s[[f]]))
  out
}

value <- one()
elapsed <- numeric(20)
for (k in 1:20) {
  t0 <- as.numeric(Sys.time())
  invisible(one())
  elapsed[k] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
