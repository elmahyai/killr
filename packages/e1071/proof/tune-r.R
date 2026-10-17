.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(e1071))
if (packageDescription("e1071")$Version != "1.7-17") stop("expected e1071 1.7-17")
json_num <- function(x) {
  paste0("[", paste(sprintf("%.17g", as.numeric(x)), collapse = ","), "]")
}
summary_of <- function(res) {
  c(
    res$best.performance,
    as.numeric(res$best.parameters$cost),
    as.numeric(res$best.parameters$gamma),
    as.numeric(res$performances$error),
    as.numeric(res$performances$dispersion)
  )
}
case_a <- function() {
  set.seed(4242)
  x <- matrix(
    c(0.0, 1.0, 1.2, 0.8, 2.5, 2.7, 2.8, 2.4, 0.1, 0.9, 2.6, 2.5),
    ncol = 2,
    byrow = TRUE
  )
  y <- factor(c("setosa", "setosa", "versicolor", "versicolor", "setosa", "versicolor"))
  ctrl <- tune.control(cross = 3, best.model = FALSE, performances = TRUE)
  res <- tune(
    "svm",
    train.x = x,
    train.y = y,
    ranges = list(cost = c(0.5, 1), gamma = c(0.3, 0.5)),
    tunecontrol = ctrl,
    kernel = "radial",
    scale = TRUE,
    cross = 0
  )
  summary_of(res)
}
case_b <- function() {
  set.seed(4242)
  x <- matrix(
    c(2.6, 2.4, 0.1, 0.3, 1.4, 1.1, 2.9, 2.2, 0.4, 0.0, 1.1, 1.6, 0.0, 0.6),
    ncol = 2,
    byrow = TRUE
  )
  y <- factor(c("virginica", "setosa", "versicolor", "virginica", "setosa", "versicolor", "setosa"))
  ctrl <- tune.control(cross = 3, best.model = FALSE, performances = TRUE)
  res <- tune(
    "svm",
    train.x = x,
    train.y = y,
    ranges = list(cost = c(0.5, 4), gamma = c(0.2, 1, 3)),
    tunecontrol = ctrl,
    kernel = "radial",
    scale = TRUE,
    cross = 0
  )
  summary_of(res)
}
one <- function() {
  c(case_a(), case_b())
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
