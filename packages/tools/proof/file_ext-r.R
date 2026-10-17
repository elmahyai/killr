show <- function(v) ifelse(is.na(v), "NA", ifelse(!nzchar(v), "<empty>", v))
one <- function() {
  x <- c("a.txt", "a.tar.gz", ".hidden", "file.", "file.c++", "a.é", "x.Y_z", "foo/bar.txt.bak", NA)
  c(show(tools::file_ext(x)), show(tools::file_ext(1.5)), show(tools::file_ext(1)), if (identical(tools::file_ext(NULL), logical(0))) "<logical0>" else "BAD")
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(value, collapse = " "), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
