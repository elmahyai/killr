suppressPackageStartupMessages(library(withr))

emit <- function(value, ms) {
  items <- vapply(value, function(x) if (is.character(x)) paste0('"', x, '"') else sprintf("%.17g", x), "")
  cat(sprintf('{"value": [%s], "median_ms": %.6f}\n', paste(items, collapse=", "), ms))
}

one <- function(name) {
  before <- search()
  if (name %in% c("local_environment", "with_environment")) {
    env <- list2env(list(value=42))
    inside <- if (name == "local_environment") local({ local_environment(env, name="withr-proof-env"); get("value") }) else with_environment(env, get("value"), name="withr-proof-env")
    return(c(inside, as.numeric(!("withr-proof-env" %in% search()))))
  }
  if (name %in% c("local_package", "with_package")) {
    inside <- if (name == "local_package") local({ local_package("compiler"); "package:compiler" %in% search() }) else with_package("compiler", "package:compiler" %in% search())
    return(c(as.numeric(inside), as.numeric(identical(search(), before))))
  }
  if (name %in% c("local_namespace", "with_namespace")) {
    ns <- format(asNamespace("stats"))
    inside <- if (name == "local_namespace") local({ local_namespace("stats"); ns %in% search() }) else with_namespace("stats", ns %in% search())
    return(c(as.numeric(inside), as.numeric(identical(search(), before))))
  }
  before <- .libPaths()
  path <- file.path(tempdir(), "withr-proof-lib")
  dir.create(path, showWarnings=FALSE)
  if (name %in% c("local_libpaths", "with_libpaths")) {
    inside <- if (name == "local_libpaths") local({ local_libpaths(path); .libPaths()[1] }) else with_libpaths(path, .libPaths()[1])
    return(c(as.numeric(identical(normalizePath(inside), normalizePath(path))), as.numeric(identical(.libPaths(), before))))
  }
  if (name %in% c("local_temp_libpaths", "with_temp_libpaths")) {
    inside <- if (name == "local_temp_libpaths") local({ local_temp_libpaths(); c(.libPaths()[1] != "", identical(.libPaths()[-1], before)) }) else with_temp_libpaths(c(.libPaths()[1] != "", identical(.libPaths()[-1], before)))
    return(c(as.numeric(all(inside)), as.numeric(identical(.libPaths(), before))))
  }
  stop("unknown proof")
}

run <- function(name) {
  value <- one(name)
  elapsed <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- Sys.time(); one(name); elapsed[i] <- as.numeric(difftime(Sys.time(), t0, units="secs")) * 1000
  }
  emit(value, median(elapsed))
}
