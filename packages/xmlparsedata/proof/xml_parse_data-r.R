library(xmlparsedata)

pd <- data.frame(
  line1 = c(1L, 1L, 1L, 1L, 1L),
  col1 = c(1L, 1L, 3L, 5L, 5L),
  line2 = c(1L, 1L, 1L, 1L, 1L),
  col2 = c(5L, 1L, 3L, 5L, 5L),
  id = c(5L, 1L, 2L, 3L, 4L),
  parent = c(0L, 5L, 5L, 5L, 3L),
  token = c("expr", "SYMBOL", "'+'", "NUM_CONST", "expr"),
  terminal = c(FALSE, TRUE, TRUE, TRUE, FALSE),
  text = c("", "x", "+", "1", ""),
  stringsAsFactors = FALSE
)
writeLines(
  xml_parse_data(pd, pretty = FALSE),
  "packages/xmlparsedata/docs/output/xml_parse_data-r.txt"
)
invisible(replicate(1, xml_parse_data(pd, pretty = FALSE)))
times <- numeric(20)
for (i in seq_along(times)) {
  t0 <- Sys.time()
  invisible(xml_parse_data(pd, pretty = FALSE))
  times[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs")) * 1000
}
cat(sprintf("r_ms=%.9f\n", median(times)))
