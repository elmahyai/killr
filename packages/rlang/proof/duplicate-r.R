.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(rlang))
if (as.character(packageVersion("rlang")) != "1.3.0") {
  stop("expected rlang 1.3.0")
}
one <- function() {
  x <- list(1:3, 4:6)
  d <- duplicate(x)
  ds <- duplicate(x, shallow = TRUE)
  e <- env(a = 1)
  paste(
    identical(d, x),
    !identical(obj_address(d), obj_address(x)),
    !identical(obj_address(d[[1]]), obj_address(x[[1]])),
    identical(obj_address(ds[[1]]), obj_address(x[[1]])),
    !identical(obj_address(ds), obj_address(x)),
    identical(duplicate(e), e),
    identical(duplicate(sym("foo")), sym("foo")),
    sep = ","
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
shown <- enc2utf8(paste(as.character(value), collapse = "|"))
shown <- gsub("\n", " / ", shown, fixed = TRUE)
cat("VALUE ", shown, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
