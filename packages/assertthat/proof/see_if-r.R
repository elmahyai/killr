suppressPackageStartupMessages(library(assertthat))

show <- function(res) {
  if (isTRUE(res)) "TRUE\n" else if (is.character(res)) paste0(res, "\n") else paste0(attr(res, "msg"), "\n")
}
one <- function() {
  x <- 1
  out <- character()
  out <- c(out, show(see_if(is.character(x))))
  out <- c(out, show(see_if(length(x) == 3)))
  out <- c(out, show(see_if(is.scalar("a"))))
  out <- c(out, show(see_if(is.string(1:3))))
  out <- c(out, show(see_if(is.dir(17))))
  out <- c(out, show(see_if(is.dir("asdf"))))
  out <- c(out, show(see_if(5 < 3, msg = "Five is not smaller than three")))
  out <- c(out, show(see_if(noNA(c(TRUE, NA)))))
  x <- 2
  out <- c(out, show(see_if(are_equal(x, 1.9))))
  out <- c(out, show(see_if(are_equal(x, 1.999, tol = 0.01))))
  out <- c(out, show(see_if(any(c(FALSE, FALSE)))))
  out <- c(out, show(see_if(5 != 5)))
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
