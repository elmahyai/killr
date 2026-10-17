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
  specs <- list(
    c("l", "l", "l"),
    "lll",
    "l{2in}ll",
    c("l", "|", "l", "l"),
    c("r", "r", "r"),
    "lcr"
  )
  for (i in seq_along(specs)) {
    x <- make_xt(i)
    x <- `align<-`(x, specs[[i]])
    out[[paste0("align_", i)]] <- attr(x, "align", exact = TRUE)
  }
  xwide <- structure(
    matrix(seq_len(15), 3, 5),
    class = c("xtable", "matrix"),
    align = rep("l", 6),
    digits = rep(0, 6),
    display = rep("d", 6)
  )
  xwide <- `align<-`(xwide, c("l", "c", "c", "c", "c", "c"))
  out$wide <- attr(xwide, "align", exact = TRUE)
  out$err_len <- as.character(message_of(`align<-`(make_xt(1L), c("l", "l"))))
  out$err_class <- as.character(
    message_of(`align<-`(structure(1, class = "foo"), "lll"))
  )
  out$err_brace <- as.character(message_of(`align<-`(make_xt(2L), "l{2in")))
  repeated <- character(0)
  for (j in seq_len(400)) {
    x <- make_xt(j)
    val <- paste0(rep("l", ncol(x) + 1), collapse = "")
    x <- `align<-`(x, val)
    repeated <- c(repeated, attr(x, "align", exact = TRUE))
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
