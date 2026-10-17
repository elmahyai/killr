library(sass)

out <- file.path(getwd(), "packages", "sass", "proof", "outputs")
dir.create(out, recursive = TRUE, showWarnings = FALSE)
td <- tempfile("sass-proof-")
dir.create(td)
f <- file.path(td, "input.scss")
writeLines("$x: 1px;", f, useBytes = TRUE)

cases <- list(
  sass_import = function() sass_import("a\\b\"c'd"),
  sass_file = function() sass_file(f),
  sass_file_cache = function() sass_file_cache(td),
  sass_cache_context_dir = function() sass_cache_context_dir(),
  sass_cache_get_dir = function() sass_cache_get_dir(td, create = TRUE),
  sass_cache_set_dir = function() sass_cache_set_dir(td, sass_file_cache(td)),
  sass_cache_get = function() sass_cache_get(),
  sass_cache_options = function() sass_cache_options(NULL, NULL),
  sass_bundle = function() sass_bundle(theme = c("a"))
)
results <- list()
for (nm in names(cases)) {
  value <- tryCatch(cases[[nm]](), error = function(e) paste0("ERROR: ", conditionMessage(e)))
  times <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- Sys.time()
    invisible(tryCatch(cases[[nm]](), error = function(e) NULL))
    times[[i]] <- as.numeric(difftime(Sys.time(), t0, units = "secs")) * 1000
  }
  capture.output(str(value), file = file.path(out, paste0(nm, "_r.txt")))
  results[[nm]] <- list(r_ms = median(times), value = capture.output(str(value)))
}
b <- sass_bundle(theme = "a", other = "b")
value <- sass_bundle_remove(b, "other")
times <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time()
  invisible(sass_bundle_remove(sass_bundle(theme = "a", other = "b"), "other"))
  times[[i]] <- as.numeric(difftime(Sys.time(), t0, units = "secs")) * 1000
}
capture.output(str(value), file = file.path(out, "sass_bundle_remove_r.txt"))
results$sass_bundle_remove <- list(r_ms = median(times), value = capture.output(str(value)))
saveRDS(results, file.path(out, "r_results.rds"))
if (requireNamespace("jsonlite", quietly = TRUE)) {
  jsonlite::write_json(results, file.path(out, "r_results.json"), auto_unbox = TRUE, pretty = TRUE)
}
