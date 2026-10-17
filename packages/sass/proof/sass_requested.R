suppressPackageStartupMessages(library(sass))

root <- normalizePath(file.path("packages", "sass"))
proof <- file.path(root, "proof")
out <- file.path(root, "docs", "output")
dir.create(out, recursive = TRUE, showWarnings = FALSE)
td <- tempfile("sass-requested-")
dir.create(td)
scss <- file.path(td, "input.scss")
writeLines(c("/*-- scss:rules --*/", "a {", "  color: red;", "}"), scss)
attachment <- file.path(td, "attachment.txt")
writeLines("attachment", attachment)
destination <- file.path(td, "attachments")
dir.create(destination)

bundle <- sass_bundle(theme = "a", other = "b")
layer <- sass_layer(rules = "a { color: red; }",
                    file_attachments = c(x = attachment))
options <- sass_options(output_style = "expanded", include_path = "x",
                        indent_width = 3)

cases <- list(
  sass_import = function() sass_import("a\\b\"c'd"),
  sass_file = function() sass_file(scss),
  sass_bundle = function() sass_bundle(theme = "a", other = "b"),
  sass_bundle_remove = function() sass_bundle_remove(bundle, "other"),
  sass_cache_options = function() sass_cache_options(NULL, NULL),
  sass_layer = function() sass_layer(rules = "a { color: red; }",
                                     file_attachments = c(x = attachment)),
  sass_layer_file = function() sass_layer_file(scss),
  sass_layer_merge = function() sass_layer_merge(layer, sass_layer_file(scss)),
  sass_options = function() sass_options(output_style = "expanded",
                                         include_path = "x", indent_width = 3),
  sass_options_get = function() {
    sass_options_set(output_style = "compressed")
    value <- sass_options_get()
    sass_options_set(NULL)
    value
  },
  sass_options_set = function() {
    sass_options_set(output_style = "compressed")
    sass_options_set(NULL)
    NULL
  },
  sass_partial = function() sass_partial("a { color: red; }", bundle),
  write_file_attachments = function() {
    write_file_attachments(c(x = attachment), destination)
    NULL
  }
)

summary <- function(name, value) {
  if (name == "sass_import") return(as.character(value))
  if (name == "sass_file") return(gsub("^@import \"|\";$", "", as.character(value)))
  if (name == "sass_bundle" || name == "sass_bundle_remove")
    return(paste(names(value$layers), collapse = "|"))
  if (name == "sass_cache_options")
    return(paste(c(value$cache, value$dir), collapse = "|"))
  if (name == "sass_layer") return(paste(length(value$layers), value$layers[[1]]$rules, sep = "|"))
  if (name == "sass_layer_file")
    return(paste(length(value$layers), paste(value$layers[[1]]$rules, collapse = "\n"), sep = "|"))
  if (name == "sass_layer_merge") return(as.character(length(value$layers)))
  if (name == "sass_options")
    return(paste(value$precision, value$output_style, value$include_path,
                 nchar(value$indent), sep = "|"))
  if (name == "sass_options_get") return(as.character(value$output_style))
  if (name == "sass_partial") return(gsub("[\r\n]+$", "", as.character(value)))
  if (name == "sass_options_set" || name == "write_file_attachments") return("NULL")
  paste(capture.output(str(value)), collapse = "\n")
}

results <- list()
for (name in names(cases)) {
  value <- tryCatch(cases[[name]](), error = function(e) structure(
    paste0("ERROR: ", conditionMessage(e)), class = "proof_error"))
  untimed <- summary(name, value)
  times <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- Sys.time()
    tryCatch(cases[[name]](), error = function(e) NULL)
    times[[i]] <- as.numeric(difftime(Sys.time(), t0, units = "secs")) * 1000
  }
  writeLines(untimed, file.path(out, paste0(name, "_r.txt")))
  results[[name]] <- c(value = untimed, r_ms = median(times))
}
writeLines(vapply(names(results), function(name)
  paste(name, results[[name]][["r_ms"]], sep = "\t"), character(1)),
           file.path(proof, "sass_requested_r_timing.txt"))
writeLines(vapply(results, function(x) paste(names(x), x, sep = "=", collapse = "\n"),
                  character(1)),
           file.path(proof, "sass_requested_r_results.txt"))
