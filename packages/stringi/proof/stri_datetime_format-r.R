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

instant <- stri_datetime_create(2015, 12, 31, 23, 59, 59, tz = "UTC")
shown <- stri_datetime_format(instant, "uuuu-MM-dd HH:mm:ss", tz = "UTC")
writeLines(
  paste0("stri_datetime_format of 2015-12-31 23:59:59 UTC is ", shown, "."),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_datetime_format-r.txt"
)

one <- function() {
  c(
    stri_datetime_format(instant, "uuuu-MM-dd HH:mm:ss", tz = "UTC"),
    stri_datetime_format(instant, "date_full", tz = "UTC", locale = "en_US"),
    stri_datetime_format(instant, "time_full", tz = "UTC", locale = "en_US"),
    stri_datetime_format(instant, "time_relative_full", tz = "UTC", locale = "en_US"),
    stri_datetime_format(instant, "datetime_relative_medium", tz = "UTC", locale = "en_US"),
    stri_datetime_format(instant, "date_short", tz = "UTC", locale = "C"),
    stri_datetime_format(instant, "date_short", tz = "UTC", locale = "  en_US  "),
    stri_datetime_format(
      instant, "yyyy.MM.dd 'at' HH:mm:ss zzz", tz = "Europe/Warsaw", locale = "pl_PL"
    ),
    stri_datetime_format(c(instant, NA), c("uuuu", NA), tz = "UTC"),
    stri_datetime_format("2015-01-01", "uuuu-MM-dd HH:mm:ss", tz = "UTC")
  )
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
