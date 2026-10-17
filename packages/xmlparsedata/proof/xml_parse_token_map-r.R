library(xmlparsedata)
lines <- paste(names(xml_parse_token_map), unname(xml_parse_token_map), sep = "\t")
writeLines(lines, "packages/xmlparsedata/docs/output/xml_parse_token_map-r.txt")
invisible(replicate(1, xml_parse_token_map))
times <- numeric(20)
for (i in seq_along(times)) {
  t0 <- Sys.time()
  invisible(xml_parse_token_map)
  times[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs")) * 1000
}
cat(sprintf("r_ms=%.9f\n", median(times)))
