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
  out$default <- display(make_xt(0L))
  specs <- list(
    c("d", "f", "s"),
    c("e", "E", "g"),
    c("G", "fg", "s"),
    c("s", "d", "d"),
    rep("f", 3)
  )
  for (i in seq_along(specs)) {
    x <- make_xt(i)
    x <- `display<-`(x, specs[[i]])
    out[[paste0("disp_", i)]] <- display(x)
  }
  xwide <- structure(
    matrix(seq_len(15), 3, 5),
    class = c("xtable", "matrix"),
    align = rep("l", 6),
    digits = rep(0, 6),
    display = c("s", "d", "f", "e", "G", "fg")
  )
  out$wide_preset <- display(xwide)
  out$err_class <- as.character(message_of(display(structure(1, class = "foo"))))
  out$err_len <- as.character(message_of(`display<-`(make_xt(1L), c("d", "f"))))
  out$err_mode <- as.character(message_of(`display<-`(make_xt(1L), c("d", "f", "x"))))
  repeated <- character(0)
  modes <- c("d", "f", "e", "E", "g", "G", "fg", "s")
  for (j in seq_len(400)) {
    x <- make_xt(j)
    k <- ncol(x) + 1
    val <- modes[((seq_len(k) + j - 2L) %% length(modes)) + 1L]
    x <- `display<-`(x, val)
    repeated <- c(repeated, display(x))
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
