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
json_vec_chr <- function(x) {
  paste0("[", paste(vapply(x, json_str, ""), collapse = ","), "]")
}
json_vec_num <- function(x) {
  parts <- vapply(x, function(v) {
    if (is.na(v)) "null" else format(v, digits = 17, scientific = TRUE)
  }, "")
  paste0("[", paste(parts, collapse = ","), "]")
}

frame_to_json <- function(pals) {
  paste0(
    "{",
    '"names":', json_vec_chr(rownames(pals)), ",",
    '"type":', json_vec_chr(as.character(pals$type)), ",",
    '"h1":', json_vec_num(pals$h1), ",",
    '"h2":', json_vec_num(pals$h2), ",",
    '"h3":', json_vec_num(pals$h3), ",",
    '"c1":', json_vec_num(pals$c1), ",",
    '"c2":', json_vec_num(pals$c2), ",",
    '"c3":', json_vec_num(pals$c3), ",",
    '"l1":', json_vec_num(pals$l1), ",",
    '"l2":', json_vec_num(pals$l2), ",",
    '"l3":', json_vec_num(pals$l3), ",",
    '"p1":', json_vec_num(pals$p1), ",",
    '"p2":', json_vec_num(pals$p2), ",",
    '"p3":', json_vec_num(pals$p3), ",",
    '"p4":', json_vec_num(pals$p4), ",",
    '"cmax1":', json_vec_num(pals$cmax1), ",",
    '"cmax2":', json_vec_num(pals$cmax2),
    "}"
  )
}

one <- function() {
  list(
    all = divergingx_palettes(),
    geyser = divergingx_palettes("Geyser"),
    multi = divergingx_palettes(c("geyser", "armyrose")),
    partial = divergingx_palettes("spec")
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
    '{"all":%s,"geyser":%s,"multi":%s,"partial":%s,',
    '"median_ms":%.17g}\n'
  ),
  frame_to_json(value$all),
  frame_to_json(value$geyser),
  frame_to_json(value$multi),
  frame_to_json(value$partial),
  median(elapsed) * 1000
))
