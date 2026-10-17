suppressPackageStartupMessages(library(fontawesome))
dep <- fa_html_dependency()
result <- list(
  name = dep$name, version = dep$version, src = dep$src,
  package = dep$package, meta = dep$meta, script = dep$script,
  stylesheet = dep$stylesheet, head = dep$head,
  attachment = dep$attachment, all_files = dep$all_files
)
invisible(result)
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time()
  dep <- fa_html_dependency()
  result <- list(
    name = dep$name, version = dep$version, src = dep$src,
    package = dep$package, meta = dep$meta, script = dep$script,
    stylesheet = dep$stylesheet, head = dep$head,
    attachment = dep$attachment, all_files = dep$all_files
  )
  elapsed[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
}
cat(sprintf("r_ms %.17g\n", median(elapsed) * 1000))
cat(jsonlite::toJSON(result, auto_unbox = TRUE, null = "null"), "\n")
