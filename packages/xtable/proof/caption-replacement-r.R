suppressPackageStartupMessages(library(xtable))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageDescription("xtable")$Version == "1.8-8")

example <- "/home/ahmed/killr_projects/killr/packages/xtable/docs/output/caption-replacement-r.txt"
x <- xtable(data.frame(a = 1:3, b = 4:6))
caption(x) <- "Table caption for the example"
sink(example)
print(caption(x))
caption(x) <- c("First line", "Second line")
print(caption(x))
sink()

message_of <- function(expr) {
  tryCatch(expr, error = function(e) conditionMessage(e))
}

make_xt <- function(i) {
  xtable(data.frame(a = seq_len(3 + (i %% 4)), b = seq_len(3 + (i %% 4))))
}

one <- function() {
  out <- list()
  caps <- list(
    "A short caption",
    c("Line one", "Line two"),
    character(0),
    NA_character_,
    NA,
    "café & naïve",
    "",
    c("", "second")
  )
  for (i in seq_along(caps)) {
    x <- make_xt(i)
    x <- `caption<-`(x, caps[[i]])
    out[[paste0("cap_", i)]] <- attr(x, "caption", exact = TRUE)
  }
  xmat <- structure(
    matrix(seq_len(12), 3, 4),
    class = c("xtable", "matrix"),
    align = c("l", "l", "l", "l", "l"),
    digits = c(0, 0, 0, 0, 0),
    display = c("d", "d", "d", "d", "d")
  )
  xmat <- `caption<-`(xmat, "matrix table")
  out$matrix_cap <- attr(xmat, "caption", exact = TRUE)
  out$int_cap <- attr(`caption<-`(make_xt(99L), 1:2), "caption", exact = TRUE)
  out$err_len <- as.character(message_of(`caption<-`(make_xt(1L), c("a", "b", "c"))))
  out$err_class <- as.character(message_of(`caption<-`(structure(1, class = "foo"), "x")))
  repeated <- character(0)
  for (j in seq_len(400)) {
    x <- make_xt(j)
    x <- `caption<-`(x, paste0("cap-", j))
    repeated <- c(repeated, attr(x, "caption", exact = TRUE))
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
