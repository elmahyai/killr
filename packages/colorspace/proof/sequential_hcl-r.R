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
    default = sequential_hcl(7, h = 260, c = 80, l = c(35, 95), power = 1),
    defaults = sequential_hcl(7),
    power_vec = sequential_hcl(7, h = 245, c = c(40, 75, 0), l = c(30, 95), power = c(0.8, 1.4)),
    triangular = sequential_hcl(7, h = 245, c = c(40, 75, 0), l = c(30, 95), power = 1),
    multi_hue = sequential_hcl(7, h = c(260, 220), c = c(50, 75, 0), l = c(30, 95), power = 1),
    linear_chroma = sequential_hcl(7, h = c(260, 60), c = 60, l = c(40, 95), power = 1),
    palette = sequential_hcl(7, palette = "Blues 3"),
    palette_override = sequential_hcl(7, palette = "Viridis", l2 = 85),
    rev = sequential_hcl(7, h = 260, c = 80, l = c(35, 95), power = 1, rev = TRUE),
    alpha = sequential_hcl(
      5, h = 260, c = 80, l = c(35, 95), power = 1, alpha = c(1, 0.5, 0.25, 0.5, 1)
    ),
    no_fixup = sequential_hcl(7, h = 260, c = 120, l = c(35, 95), power = 1, fixup = FALSE),
    grays = sequential_hcl(11, palette = "Grays"),
    bulk = sequential_hcl(256, h = 260, c = 80, l = c(30, 90), power = 1.5)
  )
}

invisible(sequential_hcl(7, h = 260, c = 80, l = c(35, 95), power = 1))
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

cat(sprintf(
  paste0(
    '{"default":%s,"defaults":%s,"power_vec":%s,"triangular":%s,"multi_hue":%s,',
    '"linear_chroma":%s,"palette":%s,"palette_override":%s,"rev":%s,"alpha":%s,',
    '"no_fixup":%s,"grays":%s,"bulk":%s,"median_ms":%.17g}\n'
  ),
  json_vec(unname(value$default)),
  json_vec(unname(value$defaults)),
  json_vec(unname(value$power_vec)),
  json_vec(unname(value$triangular)),
  json_vec(unname(value$multi_hue)),
  json_vec(unname(value$linear_chroma)),
  json_vec(unname(value$palette)),
  json_vec(unname(value$palette_override)),
  json_vec(unname(value$rev)),
  json_vec(unname(value$alpha)),
  json_vec(unname(value$no_fixup)),
  json_vec(unname(value$grays)),
  json_vec(unname(value$bulk)),
  median(elapsed) * 1000
))
