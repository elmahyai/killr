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
    example12 = terrain_hcl(12),
    default7 = terrain_hcl(7),
    custom = terrain_hcl(9, h = c(140, 20), c. = c(70, 5), l = c(55, 92), power = c(0.15, 1.05)),
    single = terrain_hcl(1),
    empty = terrain_hcl(0),
    alpha_vec = terrain_hcl(5, alpha = c(1, 0.5, 0.25, 0.5, 1)),
    alpha_scalar = terrain_hcl(4, alpha = 0.75),
    no_fixup = terrain_hcl(8, fixup = FALSE),
    bulk = terrain_hcl(256)
  )
}

invisible(terrain_hcl(12))
dir.create("docs/output", recursive = TRUE, showWarnings = FALSE)
writeLines(as.character(terrain_hcl(12)), "docs/output/terrain_hcl-r.txt")
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

cat(sprintf(
  paste0(
    '{"example12":%s,"default7":%s,"custom":%s,"single":%s,"empty":%s,',
    '"alpha_vec":%s,"alpha_scalar":%s,"no_fixup":%s,"bulk":%s,',
    '"median_ms":%.17g}\n'
  ),
  json_vec(unname(value$example12)),
  json_vec(unname(value$default7)),
  json_vec(unname(value$custom)),
  json_vec(unname(value$single)),
  json_vec(unname(value$empty)),
  json_vec(unname(value$alpha_vec)),
  json_vec(unname(value$alpha_scalar)),
  json_vec(unname(value$no_fixup)),
  json_vec(unname(value$bulk)),
  median(elapsed) * 1000
))
