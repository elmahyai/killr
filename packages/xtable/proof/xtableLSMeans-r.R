suppressPackageStartupMessages(library(xtable))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageDescription("xtable")$Version == "1.8-8")

one <- function() {
  x <- data.frame(est = c(1, 2, 3), trt = factor(c("a", "b", "a")), se = c(0.1, 0.2, 0.3))
  attr(x, "estName") <- "lsmean"
  attr(x, "mesg") <- "note"
  xl <- xtableLSMeans(x, caption = "LS", label = "tab:ls")
  list(
    class = class(xl),
    len = length(xl),
    message = attr(xl, "message"),
    sub1 = attr(xl[[1]], "subheading"),
    sub2 = attr(xl[[2]], "subheading"),
    ncol1 = ncol(xl[[1]])
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"median_ms":%.17g,"value":', median(elapsed) * 1000))
cat(toJSON(value, auto_unbox = TRUE, na = "null", null = "null"))
cat("}\n")
