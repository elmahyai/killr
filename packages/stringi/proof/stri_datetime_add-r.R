.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")

js <- function(s) {
  if (is.na(s)) return("null")
  s <- enc2utf8(as.character(s))
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub("\"", "\\\"", s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
  s <- gsub("\r", "\\r", s, fixed = TRUE)
  s <- gsub("\t", "\\t", s, fixed = TRUE)
  paste0("\"", s, "\"")
}

to_json <- function(x) {
  if (is.null(x)) return("null")
  if (inherits(x, "POSIXct")) x <- unclass(x)
  if (is.data.frame(x) || (is.list(x) && !is.null(names(x)))) {
    nms <- names(x)
    parts <- vapply(seq_along(x), function(i) {
      paste0(js(nms[[i]]), ":", to_json(x[[i]]))
    }, "")
    return(paste0("{", paste(parts, collapse = ","), "}"))
  }
  if (is.list(x)) {
    if (length(x) == 0) return("[]")
    return(paste0("[", paste(vapply(x, to_json, ""), collapse = ","), "]"))
  }
  if (is.logical(x)) {
    bits <- ifelse(is.na(x), "null", ifelse(x, "true", "false"))
    if (length(x) == 1) return(bits[[1]])
    return(paste0("[", paste(bits, collapse = ","), "]"))
  }
  if (is.character(x)) {
    if (length(x) == 0) return("[]")
    if (length(x) == 1) return(js(x[[1]]))
    return(paste0("[", paste(vapply(x, js, ""), collapse = ","), "]"))
  }
  if (is.numeric(x)) {
    bits <- ifelse(is.na(x), "null", sprintf("%.17g", x))
    if (length(x) == 1) return(bits[[1]])
    return(paste0("[", paste(bits, collapse = ","), "]"))
  }
  stop("unsupported JSON value")
}

example <- stri_datetime_add(
  stri_datetime_create(2024, 1, 31, tz = "UTC"), 1, units = "months", tz = "UTC"
)
writeLines(
  paste0(
    "stri_datetime_add of 2024-01-31 plus one month returns ",
    sprintf("%.0f", unclass(example)),
    "."
  ),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_datetime_add-r.txt"
)

one <- function() {
  jan2015 <- stri_datetime_create(2015, 1, 31, tz = "UTC")
  jan2024 <- stri_datetime_create(2024, 1, 31, tz = "UTC")
  spring <- stri_datetime_create(2015, 3, 28, 12, tz = "Europe/Brussels")
  start <- stri_datetime_create(2025, 4, 20, tz = "UTC")
  epoch <- stri_datetime_create(2015, 1, 1, tz = "UTC")
  unclass(c(
    stri_datetime_add(jan2024, 1, "months", tz = "UTC"),
    stri_datetime_add(jan2015, 1, units = "mo", tz = "UTC"),
    stri_datetime_add(start, 1, "years", tz = "UTC", locale = "@calendar=hebrew"),
    stri_datetime_add(start, 1, "years", tz = "UTC"),
    stri_datetime_add(spring, 1, "days", tz = "Europe/Brussels"),
    stri_datetime_add(spring, 24, "hours", tz = "Europe/Brussels"),
    stri_datetime_add(epoch, c(1, NA), "days", tz = "UTC"),
    stri_datetime_add(c(epoch, NA), 1, "days", tz = "UTC"),
    stri_datetime_add("2015-01-01", 0, "seconds"),
    stri_datetime_add(epoch, 1500, "milliseconds", tz = "UTC"),
    stri_datetime_add(epoch, 1.9, "days", tz = "UTC")
  ))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":%s,\"median_ms\":%.17g}\n",
  to_json(value),
  stats::median(elapsed) * 1000
))
