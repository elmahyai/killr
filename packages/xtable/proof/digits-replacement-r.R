suppressPackageStartupMessages(library(xtable))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageDescription("xtable")$Version == "1.8-8")

message_of <- function(expr) {
  tryCatch(expr, error = function(e) conditionMessage(e))
}

make_xt <- function(i) {
  n <- 3 + (i %% 4)
  xtable(data.frame(a = seq_len(n), b = seq_len(n)))
}

one <- function() {
  out <- list()
  out$default <- digits(make_xt(0L))
  specs <- list(
    4,
    c(1, 2, 3),
    c(0, 0, 0),
    c(5, 4, 3),
    0
  )
  for (i in seq_along(specs)) {
    x <- make_xt(i)
    x <- `digits<-`(x, specs[[i]])
    out[[paste0("dig_", i)]] <- digits(x)
  }
  xmat <- structure(
    matrix(seq_len(12), 3, 4),
    class = c("xtable", "matrix"),
    align = rep("l", 5),
    digits = rep(0, 5),
    display = rep("d", 5)
  )
  xmat <- `digits<-`(xmat, matrix(seq_len(15), 3, 5))
  out$matrix_dig <- digits(xmat)
  xwide <- structure(
    matrix(seq_len(6), 2, 3),
    class = c("xtable", "matrix"),
    align = rep("l", 4),
    digits = matrix(c(1, 2, 3, 4, 5, 6, 7, 8), 2, 4),
    display = rep("d", 4)
  )
  out$wide_preset <- digits(xwide)
  out$err_class <- as.character(message_of(digits(structure(1, class = "foo"))))
  out$err_len <- as.character(message_of(`digits<-`(make_xt(1L), c(1, 2))))
  out$err_numeric <- as.character(message_of(`digits<-`(make_xt(1L), c("a", "b", "c"))))
  repeated <- numeric(0)
  for (j in seq_len(400)) {
    x <- make_xt(j)
    x <- `digits<-`(x, j %% 7)
    repeated <- c(repeated, digits(x))
  }
  out$repeated <- repeated
  out
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"median_ms":%.17g,"value":', median(elapsed) * 1000))
cat(toJSON(value, auto_unbox = FALSE, na = "null", null = "null"))
cat("}\n")
