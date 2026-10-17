# Shared canonical forms for the sass html-dependency proofs.
# Sourced after _sass_r_common.R. The caller defines `here` (the proof directory).
#
# A dependency is canonical when its stylesheet text, its font files (md5),
# and its identity match. A tagFunction (what font helpers return) is rendered
# by calling it, so a local = TRUE dependency is built from the fixture cache.

proof_fixture <- function(...) file.path(here, "fixtures", ...)

# Offline stand-in for sass's file cache, read by R and by Python.
# The manifest keys are the Google href and the font basenames. R's cache
# keys are rlang hashes, so this stub maps each hash to the same fixture file.
google_fixture_cache <- function() {
  fx <- proof_fixture("google_local")
  m <- jsonlite::fromJSON(file.path(fx, "manifest.json"))
  files <- list()
  files[[ns$hash_with_user_agent(m$href)]] <- file.path(fx, m$css)
  for (nm in names(m$fonts)) {
    files[[ns$hash_with_user_agent(nm)]] <- file.path(fx, m$fonts[[nm]])
  }
  list(
    get_file = function(key, outfile, overwrite = TRUE) {
      src <- files[[key]]
      if (is.null(src)) return(FALSE)
      file.copy(src, outfile, overwrite = overwrite)
    },
    set_file = function(key, file, ...) FALSE
  )
}

# Canonical form of one html dependency.
# x is a tagFunction (font helpers) or an htmlDependency object.
canon_html <- function(x) {
  kind <- "html"
  href <- NULL
  d <- x
  if (is.function(x)) {
    e <- environment(x)
    f <- e$dep_func
    kind <- if (identical(f, ns$font_dep_face)) {
      "face"
    } else if (identical(f, ns$font_dep_link)) {
      "link"
    } else if (identical(f, ns$font_dep_google_local)) {
      "google_local"
    } else {
      "unknown"
    }
    if (kind %in% c("link", "google_local")) href <- e$x$href
    d <- x()
  }
  stylesheet <- if (!is.null(d$stylesheet)) {
    paste(readLines(file.path(d$src$file, d$stylesheet), warn = FALSE), collapse = "\n")
  }
  files <- if (isTRUE(d$all_files)) {
    nms <- sort(list.files(d$src$file), method = "radix")
    lapply(nms, function(nm) {
      list(name = nm, md5 = unname(tools::md5sum(file.path(d$src$file, nm))))
    })
  }
  list(
    name = d$name,
    version = as.character(d$version),
    kind = kind,
    href = href,
    head = d$head,
    stylesheet = stylesheet,
    files = files
  )
}

canon_deps <- function(deps) {
  if (is.null(deps)) return(NULL)
  if (is.function(deps) || inherits(deps, "html_dependency")) deps <- list(deps)
  lapply(deps, canon_html)
}

# A font_collection, with each dependency rendered.
canon_collection <- function(fc) {
  deps <- fc$html_deps
  if (is.null(deps)) deps <- list()
  if (is.function(deps)) deps <- list(deps)
  list(
    families = as.list(fc$families),
    default_flag = isTRUE(fc$default_flag),
    html_deps = lapply(deps, canon_html)
  )
}

# as_sass() result: its text and its html dependencies (R attribute).
as_html_case <- function(x) {
  list(
    text = as.character(x),
    html_dependencies = canon_deps(attr(x, "html_dependencies", exact = TRUE))
  )
}
