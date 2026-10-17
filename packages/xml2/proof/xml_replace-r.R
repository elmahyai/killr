.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(xml2))
json_str <- function(s) {
  if (is.null(s) || length(s) == 0 || is.na(s)) return("null")
  cps <- utf8ToInt(enc2utf8(as.character(s)))
  if (length(cps) == 0) return('""')
  parts <- vapply(cps, function(cp) {
    if (cp == 34) paste0("\\", '"')
    else if (cp == 92) paste0("\\", "\\")
    else if (cp == 10) paste0("\\", "n")
    else if (cp == 13) paste0("\\", "r")
    else if (cp == 9) paste0("\\", "t")
    else if (cp < 32 || cp == 127 || cp > 126) sprintf("\\u%04x", cp)
    else intToUtf8(cp)
  }, "")
  paste0('"', paste(parts, collapse = ""), '"')
}
flat <- function(x) {
  if (is.null(x) || length(x) == 0) return("NA")
  if (is.logical(x)) return(paste(ifelse(is.na(x), "NA", ifelse(x, "TRUE", "FALSE")), collapse = " "))
  if (is.numeric(x)) {
    txt <- ifelse(is.na(x), "NA", ifelse(abs(x - round(x)) < 1e-8 & abs(x) < 1e15, as.character(as.integer(round(x))), format(x, trim = TRUE, scientific = FALSE)))
    return(paste(txt, collapse = " "))
  }
  paste(ifelse(is.na(x), "NA", as.character(x)), collapse = " ")
}
to_json <- function(x) {
  if (is.null(x)) return("null")
  if (is.atomic(x) && length(x) == 1) {
    if (is.na(x)) return("null")
    if (is.logical(x)) return(if (isTRUE(x)) "true" else "false")
    if (is.numeric(x)) return(sprintf("%.17g", x))
    return(json_str(x))
  }
  if (is.atomic(x)) {
    parts <- vapply(seq_along(x), function(i) {
      if (is.na(x[[i]])) "null" else to_json(x[[i]])
    }, "")
    return(paste0("[", paste(parts, collapse = ","), "]"))
  }
  stop("unsupported")
}
one <- function() {
  {x <- read_xml("<foo><bar/></foo>"); xml_replace(xml_child(x), "baz"); as.character(x)}
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', to_json(value), median(elapsed) * 1000))
