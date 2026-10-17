suppressPackageStartupMessages(library(assertthat))

show <- function(res) {
  if (isTRUE(res)) "TRUE\n" else if (is.character(res)) paste0(res, "\n") else paste0(attr(res, "msg"), "\n")
}
one <- function() {
  x <- 1
  out <- c(
    show(validate_that(is.numeric(x))),
    show(validate_that(is.character(x))),
    show(validate_that(length(x) == 3)),
    show(validate_that(is.dir("asdf"))),
    show(validate_that(FALSE, msg = "Custom message")),
    show(validate_that(5 == "i")),
    show(validate_that(any(c(FALSE, FALSE))))
  )
  x <- c(FALSE, TRUE)
  out <- c(out, show(validate_that(all(x))))
  paste0(out, collapse = "")
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(value, sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
