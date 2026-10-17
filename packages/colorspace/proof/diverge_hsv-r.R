suppressPackageStartupMessages(library(colorspace))
stopifnot(identical(packageDescription("colorspace")$Version, "2.1-4"))

json_str <- function(s) {
  if (length(s) != 1L) stop("json_str expects length 1")
  if (is.na(s)) return("null")
  s <- enc2utf8(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub("\"", "\\\"", s, fixed = TRUE)
  paste0('"', s, '"')
}
json_vec <- function(x) {
  paste0("[", paste(vapply(x, json_str, ""), collapse = ","), "]")
}

one <- function() {
  list(
    example7 = diverge_hsv(7),
    custom = diverge_hsv(9, h = c(200, 40), s = 0.85, v = 0.95, power = 1.15),
    single = diverge_hsv(1),
    empty = diverge_hsv(0),
    alpha_vec = diverge_hsv(7, alpha = c(1, 0.5, 0.25, 0.5, 1, 1, 1)),
    alpha_scalar = diverge_hsv(4, alpha = 0.75),
    no_fixup = diverge_hsv(8, fixup = FALSE),
    bulk = diverge_hsv(256)
  )
}

invisible(diverge_hsv(7))
dir.create("docs/output", recursive = TRUE, showWarnings = FALSE)
writeLines(as.character(diverge_hsv(7)), "docs/output/diverge_hsv-r.txt")
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

cat(sprintf(
  paste0(
    '{"example7":%s,"custom":%s,"single":%s,"empty":%s,',
    '"alpha_vec":%s,"alpha_scalar":%s,"no_fixup":%s,"bulk":%s,',
    '"median_ms":%.17g}\n'
  ),
  json_vec(unname(value$example7)),
  json_vec(unname(value$custom)),
  json_vec(unname(value$single)),
  json_vec(unname(value$empty)),
  json_vec(unname(value$alpha_vec)),
  json_vec(unname(value$alpha_scalar)),
  json_vec(unname(value$no_fixup)),
  json_vec(unname(value$bulk)),
  median(elapsed) * 1000
))
