# Export every MASS data set from the installed R package into mass/data/
# (one CSV table and one JSON sidecar per data set), and write the R reference
# used by proof/datasets-py.py to docs/output/datasets-r.json, with the median
# of 20 timed data() loads per data set.
# Run from packages/MASS:  Rscript proof/export-datasets-r.R
suppressPackageStartupMessages({
  library(MASS)
  library(jsonlite)
})

out_dir <- file.path("mass", "data")
ref_dir <- file.path("docs", "output")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
dir.create(ref_dir, showWarnings = FALSE, recursive = TRUE)

# Numbers as C-printf %.17g text, so every double round-trips exactly.
fmt_num <- function(v) {
  vapply(as.numeric(v), function(z) if (is.na(z)) "NA" else sprintf("%.17g", z), "")
}

load_obj <- function(n) {
  e <- new.env()
  data(list = n, package = "MASS", envir = e)
  get(n, envir = e)
}

describe <- function(n, x) {
  levs <- list()
  if (is.data.frame(x)) {
    kind <- "data.frame"
    cols <- list()
    tab <- list()
    for (cn in names(x)) {
      v <- x[[cn]]
      if (!is.null(dim(v)) || length(v) != nrow(x)) stop("unsupported column ", cn, " in ", n)
      if (is.factor(v)) {
        cols[[length(cols) + 1]] <- list(name = cn, type = "factor",
                                         levels = as.list(levels(v)), ordered = is.ordered(v))
        levs[[cn]] <- levels(v)
        cell <- as.character(v)
      } else if (is.integer(v)) {
        cols[[length(cols) + 1]] <- list(name = cn, type = "integer")
        cell <- fmt_num(v)
      } else if (is.numeric(v)) {
        cols[[length(cols) + 1]] <- list(name = cn, type = "numeric")
        cell <- fmt_num(v)
      } else if (is.character(v)) {
        cols[[length(cols) + 1]] <- list(name = cn, type = "character")
        cell <- v
      } else if (is.logical(v)) {
        cols[[length(cols) + 1]] <- list(name = cn, type = "logical")
        cell <- ifelse(is.na(v), NA, ifelse(v, "TRUE", "FALSE"))
      } else {
        stop("unsupported column type ", class(v)[1], " in ", n)
      }
      tab[[cn]] <- cell
    }
    rn <- rownames(x)
    auto <- identical(rn, as.character(seq_len(nrow(x))))
    rownames_meta <- if (auto) NULL else as.list(rn)
    tsp_meta <- NULL
    tab <- data.frame(tab, check.names = FALSE, stringsAsFactors = FALSE)
  } else if (is.ts(x)) {
    kind <- "ts"
    cols <- list(list(name = "value", type = "numeric"))
    tab <- data.frame(value = fmt_num(x), stringsAsFactors = FALSE)
    rownames_meta <- NULL
    tsp_meta <- as.list(sprintf("%.17g", tsp(x)))
  } else if (is.list(x)) {
    kind <- "list"
    if (!all(vapply(x, function(v) is.numeric(v) && is.null(dim(v)), TRUE))) {
      stop("unsupported list element in ", n)
    }
    if (length(unique(lengths(x))) != 1L) stop("list elements differ in length in ", n)
    cols <- lapply(names(x), function(cn) list(name = cn, type = "numeric"))
    tab <- data.frame(lapply(x, fmt_num), check.names = FALSE, stringsAsFactors = FALSE)
    rownames_meta <- NULL
    tsp_meta <- NULL
  } else if (is.numeric(x) && is.null(dim(x))) {
    kind <- "numeric"
    cols <- list(list(name = "value", type = "numeric"))
    tab <- data.frame(value = fmt_num(x), stringsAsFactors = FALSE)
    rownames_meta <- NULL
    tsp_meta <- NULL
  } else {
    stop("unsupported object class ", class(x)[1], " in ", n)
  }
  list(kind = kind, cols = cols, tab = tab, rownames = rownames_meta, tsp = tsp_meta,
       levels = levs)
}

items <- data(package = "MASS")$results[, "Item"]
refs <- list()
for (n in items) {
  x <- load_obj(n)
  d <- describe(n, x)

  write.table(d$tab, file.path(out_dir, paste0(n, ".csv")), sep = ",", quote = TRUE,
              row.names = FALSE, na = "NA", qmethod = "double")
  meta <- list(name = n, kind = d$kind, columns = d$cols,
               rownames = d$rownames, tsp = d$tsp)
  write_json(meta, file.path(out_dir, paste0(n, ".json")), auto_unbox = TRUE, null = "null")

  # Timing: one untimed load, then the median of 20 timed loads.
  invisible(load_obj(n))
  times <- vapply(seq_len(20), function(i) {
    t0 <- proc.time()[["elapsed"]]
    load_obj(n)
    (proc.time()[["elapsed"]] - t0) * 1000
  }, 0)

  refs[[n]] <- list(
    kind = d$kind,
    columns = as.list(names(d$tab)),
    values = lapply(d$tab, function(col) as.list(col)),
    levels = d$levels,
    rownames = d$rownames,
    tsp = d$tsp,
    ms = median(times)
  )
}

write_json(list(datasets = refs), file.path(ref_dir, "datasets-r.json"),
           auto_unbox = TRUE, null = "null", na = "null")
cat("exported", length(items), "data sets\n")
