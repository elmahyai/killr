.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

## Fixed input: gls-orthodont.csv with rows sorted by Subject then age, Subject
## levels in alphabetical order, the same data as the natural = TRUE proof and the
## fixture the Python side reads. Subject level order sets the group order in
## the log-likelihood sum, and the finite-difference apVar amplifies that order,
## so this file must not use the built-in Orthodont (levels M16, M05, ...).
## corSymm(form = ~ 1 | Subject) with glsControl(natural = FALSE): apVar holds the
## unconstrained corSymm parameters and intervals() does not convert to corNatural.
## The fits run in the untimed setup; only intervals() is timed.
script_dir <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(), value = TRUE)[1]))
d <- read.csv(file.path(script_dir, "data", "gls-orthodont.csv"), stringsAsFactors = FALSE)
d$Sex <- factor(d$Sex, levels = c("Male", "Female"))
d$Subject <- factor(d$Subject)
d <- d[order(as.character(d$Subject), d$age), ]
rownames(d) <- NULL

fits <- list(
  Orthodont_age_Sex = gls(
    distance ~ age + Sex, d, correlation = corSymm(form = ~ 1 | Subject),
    control = glsControl(natural = FALSE)
  ),
  Orthodont_age = gls(
    distance ~ age, d, correlation = corSymm(form = ~ 1 | Subject),
    control = glsControl(natural = FALSE)
  )
)

one <- function(fm) {
  a <- intervals(fm, level = 0.95, which = "all")
  c(as.numeric(a$coef), as.numeric(a$corStruct), as.numeric(a$sigma))
}

for (nm in names(fits)) {
  value <- one(fits[[nm]])
  elapsed <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    one(fits[[nm]])
    elapsed[[i]] <- as.numeric(Sys.time()) - t0
  }
  cat(sprintf(
    "%s {\"value\":[%s],\"median_ms\":%.17g}\n",
    nm, paste(sprintf("%.17g", value), collapse = ","), median(elapsed) * 1000
  ))
}
