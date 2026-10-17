suppressPackageStartupMessages(library(xtable))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageDescription("xtable")$Version == "1.8-8")

message_of <- function(expr) {
  tryCatch(expr, error = function(e) conditionMessage(e))
}

one <- function() {
  df <- data.frame(
    a = 1:3,
    b = 4:6,
    c = letters[1:3],
    d = c(TRUE, FALSE, TRUE),
    e = 1L,
    stringsAsFactors = FALSE
  )
  x <- xtable(df)
  out <- list(
    align = align(x),
    digits = digits(x),
    display = display(x),
    class = class(x),
    logical_col = as.character(x$d),
    ncol = ncol(x),
    nrow = nrow(x)
  )
  x2 <- xtable(
    data.frame(a = 1:2, b = 3:4),
    caption = "Cap",
    label = "tab:1",
    align = c("l", "l", "l"),
    digits = c(0, 1, 1),
    display = c("s", "d", "f")
  )
  out$custom <- list(
    caption = caption(x2),
    label = label(x2),
    align = align(x2),
    digits = digits(x2),
    display = display(x2)
  )
  xm <- xtable(matrix(1:6, 2, 3))
  out$matrix <- list(
    class = class(xm),
    ncol = ncol(xm),
    names = names(xm),
    align = align(xm),
    digits = digits(xm),
    display = display(xm)
  )
  out$err_class <- as.character(message_of(xtable(structure(1, class = "foo"))))
  repeated <- list()
  for (j in seq_len(200)) {
    n <- 2 + (j %% 3)
    xt <- xtable(data.frame(a = seq_len(n), b = seq_len(n)))
    repeated[[j]] <- c(align(xt), digits(xt), display(xt))
  }
  out$repeated <- unlist(repeated)
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
