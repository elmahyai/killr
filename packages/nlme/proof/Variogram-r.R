.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}

data <- data.frame(x = c(0, 1, 0.5, 2), y = c(0, 0, 1, 0.5))
obs <- c(1.2, 3.4, 2.2, 5.1)
dist_default <- as.vector(dist(c(0, 1, 0.5, 2)))
grid <- seq(0, 3, length.out = 7)

one <- function() {
  cases <- list(
    Variogram(obs, dist_default),
    Variogram(corExp(log(2.5), form = ~ x + y, metric = "eu"), distance = grid),
    Variogram(corExp(log(c(2.5, 0.2)), form = ~ x + y, nugget = TRUE, metric = "eu"),
              distance = grid),
    Variogram(corGaus(1, form = ~ x + y, metric = "man"), distance = grid),
    Variogram(Initialize(corLin(2.5, form = ~ x + y, metric = "eu"), data)),
    Variogram(Initialize(corRatio(1.8, form = ~ x + y, metric = "eu"), data),
              distance = grid, sig2 = 2),
    Variogram(Initialize(corSpher(2.5, form = ~ x + y, metric = "eu"), data), distance = grid)
  )
  unlist(lapply(cases, function(v) c(v$variog, v$dist)), use.names = FALSE)
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
