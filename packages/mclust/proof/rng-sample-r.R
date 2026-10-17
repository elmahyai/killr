.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
if (RNGkind()[1] != "Mersenne-Twister" || RNGkind()[3] != "Rejection") stop("expected default RNG kinds")

seeds <- c(1, 42, 2026, 123456789)
cases <- list(
  list("sample.int(10,10,TRUE)", function() sample.int(10, 10, replace = TRUE)),
  list("sample.int(5)", function() sample.int(5)),
  list("sample.int(100,7)", function() sample.int(100, 7)),
  list("sample.int(1000,5,TRUE)", function() sample.int(1000, 5, replace = TRUE)),
  list("sample.int(1,3,TRUE)", function() sample.int(1, 3, replace = TRUE)),
  list("sample.int(2,1)", function() sample.int(2, 1)),
  list("sample.int(7,0)", function() sample.int(7, 0)),
  list("sample.int(65537,20,TRUE)", function() sample.int(65537, 20, replace = TRUE)),
  list("sample.int(100000,30,TRUE)", function() sample.int(100000, 30, replace = TRUE)),
  list("sample.int(300000,5)", function() sample.int(300000, 5)),
  list("sample.int(2e7,5)", function() sample.int(2e7, 5)),
  list("sample.int(2e7,20000)", function() sample.int(2e7, 20000))
)

emit <- function(label, v) {
  cat(paste(c(label, sprintf("%.17g", as.numeric(v))), collapse = " "), "\n", sep = "")
}

for (s in seeds) {
  set.seed(s)
  emit(paste("seed", s, "runif20"), runif(20))
  for (cs in cases) {
    set.seed(s)
    emit(paste("seed", s, cs[[1]]), cs[[2]]())
  }
}
