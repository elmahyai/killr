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
    default5 = qualitative_hcl(5),
    custom_h = qualitative_hcl(7, h = 30, c = 50, l = 65),
    palette = qualitative_hcl(6, palette = "Set 3"),
    single = qualitative_hcl(1),
    empty = qualitative_hcl(0),
    alpha_vec = qualitative_hcl(5, alpha = c(1, 0.5, 0.25, 0.5, 1)),
    alpha_scalar = qualitative_hcl(4, alpha = 0.75),
    no_fixup = qualitative_hcl(8, c = 100, l = 50, fixup = FALSE),
    rev = qualitative_hcl(5, rev = TRUE),
    bulk = qualitative_hcl(256)
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
  paste0(
    '{"default5":%s,"custom_h":%s,"palette":%s,"single":%s,"empty":%s,',
    '"alpha_vec":%s,"alpha_scalar":%s,"no_fixup":%s,"rev":%s,"bulk":%s,',
    '"median_ms":%.17g}\n'
  ),
  json_vec(unname(value$default5)),
  json_vec(unname(value$custom_h)),
  json_vec(unname(value$palette)),
  json_vec(unname(value$single)),
  json_vec(unname(value$empty)),
  json_vec(unname(value$alpha_vec)),
  json_vec(unname(value$alpha_scalar)),
  json_vec(unname(value$no_fixup)),
  json_vec(unname(value$rev)),
  json_vec(unname(value$bulk)),
  median(elapsed) * 1000
))
