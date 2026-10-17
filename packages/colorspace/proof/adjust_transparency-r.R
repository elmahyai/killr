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

x <- c("gray", "#BEBEBE", "#BEBEBE80")
hexes <- c("#FF0000", "#00FF0080", "#336699", "#AABBCCDD")
rgb_mat <- rbind(R = c(255, 0, 0), G = c(0, 255, 0), B = c(0, 0, 255))

one <- function() {
  lab_obj <- LAB(rbind(c(50, 40, 30), c(60, -20, 50)), names = c("a", "b"))
  bulk <- sprintf("#%02X%02X%02X", 0:255, 255:0, (0:255 + 17) %% 256)
  prism <- structure(c("red", "blue", "#00FF0080"), class = "colors")
  list(
    recycle_name = adjust_transparency("black", alpha = c(0, 0.5, 1)),
    recycle_hex = adjust_transparency("#000000", alpha = c(0, 0.5, 1)),
    recycle_palette = adjust_transparency(1:3, alpha = c(0, 0.5, 1)),
    null_alpha = adjust_transparency(x, alpha = NULL),
    true_alpha = adjust_transparency(x, alpha = TRUE),
    false_alpha = adjust_transparency(x, alpha = FALSE),
    numeric_alpha = adjust_transparency(x, alpha = 0.8),
    hex_vector = adjust_transparency(hexes, alpha = 0.25),
    named = adjust_transparency(c(red = "#FF0000", blue = "#0000FF80"), alpha = TRUE),
    rgb_matrix = adjust_transparency(rgb_mat, alpha = 0.5),
    lab_object = adjust_transparency(lab_obj, alpha = c(0.2, 0.9)),
    prismatic = adjust_transparency(prism, alpha = NULL),
    bulk = adjust_transparency(bulk, alpha = TRUE)
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
    '{"recycle_name":%s,"recycle_hex":%s,"recycle_palette":%s,',
    '"null_alpha":%s,"true_alpha":%s,"false_alpha":%s,"numeric_alpha":%s,',
    '"hex_vector":%s,"named":%s,"rgb_matrix":%s,"lab_object":%s,',
    '"prismatic":%s,"bulk":%s,"median_ms":%.17g}\n'
  ),
  json_vec(unname(value$recycle_name)),
  json_vec(unname(value$recycle_hex)),
  json_vec(unname(value$recycle_palette)),
  json_vec(unname(value$null_alpha)),
  json_vec(unname(value$true_alpha)),
  json_vec(unname(value$false_alpha)),
  json_vec(unname(value$numeric_alpha)),
  json_vec(unname(value$hex_vector)),
  json_vec(unname(value$named)),
  json_vec(unname(value$rgb_matrix)),
  json_vec(unname(value$lab_object)),
  json_vec(unname(value$prismatic)),
  json_vec(unname(value$bulk)),
  median(elapsed) * 1000
))
