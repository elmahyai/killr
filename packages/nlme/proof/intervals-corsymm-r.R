.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

## Fixed input: Orthodont (gls-orthodont.csv, rows sorted by Subject then age) with
## corSymm(form = ~ 1 | Subject). glsControl natural = TRUE (the default), so the
## apVar attribute natural is TRUE and intervals() converts corSymm to corNatural.
## The fit runs in the untimed setup; only intervals() is timed.
script_dir <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(), value = TRUE)[1]))
d <- read.csv(file.path(script_dir, "data", "gls-orthodont.csv"), stringsAsFactors = FALSE)
d$Sex <- factor(d$Sex, levels = c("Male", "Female"))
d$Subject <- factor(d$Subject)
d <- d[order(as.character(d$Subject), d$age), ]
rownames(d) <- NULL

fm <- gls(distance ~ age + Sex, d, correlation = corSymm(form = ~ 1 | Subject))

one <- function() {
  a <- intervals(fm, level = 0.95, which = "all")
  c(as.numeric(a$coef), as.numeric(a$corStruct), as.numeric(a$sigma))
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
