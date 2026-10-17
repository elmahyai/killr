suppressPackageStartupMessages(library(xtable))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(packageDescription("xtable")$Version == "1.8-8")

one <- function() {
  x <- list(
    data.frame(a = 1:3, b = 4:6),
    matrix(7:10, 2, 2)
  )
  attr(x, "subheadings") <- c("Part A", "Part B")
  attr(x, "message") <- c("note", "")
  xl <- xtableList(x, caption = "List cap", label = "tab:list")
  list(
    class = class(xl),
    len = length(xl),
    caption = attr(xl, "caption"),
    label = attr(xl, "label"),
    message = attr(xl, "message"),
    sub1 = attr(xl[[1]], "subheading"),
    sub2 = attr(xl[[2]], "subheading"),
    align1 = align(xl[[1]]),
    digits1 = digits(xl[[1]]),
    display1 = display(xl[[1]]),
    nrow2 = nrow(xl[[2]])
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
