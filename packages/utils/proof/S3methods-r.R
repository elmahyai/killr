library(utils)

g <- "killrS3methodsProof"
e <- new.env()
assign(g, eval(parse(text = sprintf("function(x) UseMethod(\"%s\")", g))), envir = e)
assign(paste0(g, ".alpha"), function(x) x, envir = e)
assign(paste0(g, ".beta"), function(x) x, envir = e)

one <- function() {
  res <- utils:::.S3methods(g, envir = e, useEnv = TRUE, dropPath = TRUE)
  paste0(
    paste(sort(res), collapse = "|"),
    "\n",
    nrow(attr(res, "info")),
    "\n",
    paste(attr(res, "info")$from, collapse = "|"),
    "\n",
    paste(attr(res, "info")$generic, collapse = "|")
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(value, sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
