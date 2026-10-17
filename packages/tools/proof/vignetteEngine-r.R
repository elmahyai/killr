suppressPackageStartupMessages(library(tools))

one <- function() {
  e <- vignetteEngine("Sweave")
  miss <- tryCatch(vignetteEngine("nope"), error = function(err) conditionMessage(err))
  locked <- tryCatch(vignetteEngine("Sweave", weave = function(...) 1, tangle = function(...) 2, package = "tools"), error = function(err) conditionMessage(err))
  vignetteEngine("demo", weave = function(...) 1, tangle = function(...) 2, package = "tools")
  got <- vignetteEngine("tools::demo")
  paste0(e$name, " ", e$package, " ", e$pattern, "\n", miss, "\n", locked, "\n", got$name, " ", got$package, " ", got$pattern, "\n")
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
