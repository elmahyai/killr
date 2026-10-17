source("/tmp/xtable-src/xtable/R/sanitize.R")
source("/tmp/xtable-src/xtable/R/print.xtable.R")
source("/tmp/xtable-src/xtable/R/xtableFtable.R")

library(jsonlite)
one <- function() {
  s <- string("a  align=\"left\"  b")
  list(
    sanitize_final = sanitize.final(s, "html")$text,
    as_is = as.is(c("a", "b")),
    as_math = as.math("x"),
    ftable = {
      z <- xtableFtable(
        structure(matrix(c("A", "1"), nrow = 1),
                  row.vars = "row", col.vars = "col"),
        caption = "Cap", label = "tab:x"
      )
      unname(c(attr(z, "ftableCaption"), attr(z, "ftableLabel"),
               attr(z, "method"), attr(z, "nChars")))
    }
  )
}
value <- one()
times <- numeric(20)
for (i in seq_len(20)) {
  started <- Sys.time()
  one()
  times[i] <- as.numeric(difftime(Sys.time(), started, units = "secs")) * 1000
}
cat(jsonlite::toJSON(list(value = value, median_ms = median(times)),
                     auto_unbox = TRUE, null = "null"))
