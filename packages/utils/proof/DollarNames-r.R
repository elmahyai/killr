library(utils)

utils::rc.settings(fuzzy = FALSE)

e <- new.env()
e$foo <- 1
assign("bar", 2, e)
assign(".hidden", 3, e)

one <- function() {
  paste(sort(utils:::.DollarNames(e, "")), collapse = ",")
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(value, "\n", sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
