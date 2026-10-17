.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(sys))
one <- function() {
    warn <- ""
    err <- ""
    withCallingHandlers(
      tryCatch(eval_safe(1), error = function(e) err <<- conditionMessage(e)),
      warning = function(w) { warn <<- conditionMessage(w); invokeRestart("muffleWarning") }
    )
    paste(gsub("\n", " / ", warn), err, sep = " || ")
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
shown <- enc2utf8(paste(as.character(value), collapse = "|"))
cat("VALUE ", shown, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
