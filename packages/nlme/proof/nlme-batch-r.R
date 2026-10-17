.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}

# Write the Loblolly rows that the Python side reads (outside the timed calls).
script_dir <- function() {
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("^--file=", args, value = TRUE)
  dirname(normalizePath(sub("^--file=", "", file_arg[[1]])))
}
data_dir <- file.path(script_dir(), "data")
dir.create(data_dir, recursive = TRUE, showWarnings = FALSE)
write.csv(
  data.frame(Seed = as.character(Loblolly$Seed), age = Loblolly$age,
             height = Loblolly$height),
  file.path(data_dir, "nlme-loblolly.csv"), row.names = FALSE
)

height_data <- function() {
  age <- rep(c(2, 4, 6, 8, 10), 4)
  group <- factor(rep(LETTERS[1:4], each = 5))
  shift <- rep(c(-4, 1, 3, -2), each = 5)
  noise <- c(
    0.2, -0.1, 0.4, -0.3, 0.1, 0.0, 0.3, -0.2, 0.1, -0.4,
    -0.2, 0.2, 0.0, -0.1, 0.3, 0.1, -0.3, 0.2, 0.0, -0.2
  )
  height <- (100 + shift) + (15 - (100 + shift)) * exp(-exp(-3.2) * age) + noise
  data.frame(height, age, group)
}

one <- function() {
  # formula path: nlme dispatches to nlme.formula
  fm <- nlme(
    height ~ SSasymp(age, Asym, R0, lrc),
    data = height_data(),
    fixed = Asym + R0 + lrc ~ 1,
    random = Asym ~ 1,
    groups = ~group,
    start = c(Asym = 100, R0 = 15, lrc = -3.2)
  )
  # nlsList path: nlme dispatches to nlme.nlsList
  fit <- nlsList(height ~ SSasympOff(age, Asym, lrc, c0) | Seed, data = Loblolly,
                 start = c(Asym = 100, lrc = -1.5, c0 = 0))
  fl <- nlme(fit, random = Asym ~ 1)
  re <- as.matrix(ranef(fl))
  re <- re[order(rownames(re)), , drop = FALSE]
  # nlsList with no start, then nlme dispatches to nlme.nlsList
  fit0 <- nlsList(height ~ SSasympOff(age, Asym, lrc, c0) | Seed, data = Loblolly)
  fl0 <- nlme(fit0, random = Asym ~ 1)
  # pdDiag random structure (two random effects per Seed, diagonal covariance)
  fp <- nlme(height ~ SSasymp(age, Asym, R0, lrc), data = Loblolly,
             fixed = Asym + R0 + lrc ~ 1, random = pdDiag(Asym + R0 ~ 1),
             start = c(Asym = 103, R0 = -8.5, lrc = -3.3))
  vp <- fp$sigma^2 * pdMatrix(fp$modelStruct$reStruct)$Seed
  c(fixef(fm), fm$sigma, as.numeric(logLik(fm)), as.vector(ranef(fm)[, 1]),
    fixef(fl), fl$sigma, as.numeric(logLik(fl)), as.vector(re),
    fixef(fl0), fl0$sigma, as.numeric(logLik(fl0)),
    fixef(fp), vp[1, 1], vp[1, 2], vp[2, 2], fp$sigma, as.numeric(logLik(fp)))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
