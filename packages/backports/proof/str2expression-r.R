
.libPaths(c(path.expand("~/R/library"), .libPaths()))
ns <- asNamespace("backports")
g <- function(name) get(name, envir = ns)
flat <- function(x) {
  if (is.null(x)) return("null")
  if (is.list(x) && !is.data.frame(x)) {
    if (!length(x)) return("")
    return(paste(vapply(x, flat, ""), collapse = "|"))
  }
  if (length(x) == 0) return("")
  out <- character(length(x))
  for (i in seq_along(x)) {
    el <- x[[i]]
    if (length(el) != 1) out[[i]] <- flat(el)
    else if (is.na(el)) out[[i]] <- "NA"
    else if (is.logical(el)) out[[i]] <- if (isTRUE(el)) "true" else "false"
    else if (is.numeric(el)) out[[i]] <- sprintf("%.0f", el)
    else out[[i]] <- enc2utf8(as.character(el))
  }
  paste(out, collapse = "|")
}
esc <- function(s) {
  s <- enc2utf8(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub('"', '\\"', s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
  s <- gsub("\r", "\\r", s, fixed = TRUE)
  s
}



one <- function() {
  vapply(c("x[3] <- 1+4", "log(y)", "abc", "1.375"), function(s) paste(deparse(g("str2expression")(s)), collapse = ""), "")
}
value <- flat(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":"%s","median_ms":%.17g}\n', esc(value), median(elapsed) * 1000))

