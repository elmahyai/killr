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
json_num <- function(x) sprintf("%.17g", x)
json_mat <- function(m) {
  parts <- character(nrow(m))
  for (i in seq_len(nrow(m))) {
    parts[[i]] <- paste0(
      "[", paste(vapply(m[i, ], json_num, ""), collapse = ","), "]"
    )
  }
  paste0("[", paste(parts, collapse = ","), "]")
}
json_color <- function(obj) {
  sprintf(
    '{"space":%s,"names":null,"columns":[%s],"coords":%s}',
    json_str(class(obj)[[1L]]),
    paste(vapply(colnames(obj@coords), json_str, ""), collapse = ","),
    json_mat(obj@coords)
  )
}

hexes <- c("#FF0000", "#00FF0080", "#336699", "#AABBCCDD")
named <- c(red = "#FF0000", blue = "#0000FF")
rgb_mat <- diag(3) * 255
rownames(rgb_mat) <- c("R", "G", "B")
srgb_obj <- sRGB(c(1, 0, 0.25), c(0, 1, 0.5), c(0, 0, 0.75))
lab_obj <- LAB(c(50, 60, 70), c(40, -20, 10), c(30, 50, -40))
examples <- c("#005000", "blue", "#00BB00")

one <- function() {
  list(
    default = deutan(hexes),
    severity = deutan(hexes, severity = 0.6),
    zero = deutan(hexes, severity = 0),
    named = deutan(named),
    colors = deutan(c("red", "blue", "darkgreen")),
    palette = deutan(1:3),
    rgb_matrix = deutan(rgb_mat),
    srgb_object = deutan(srgb_obj),
    lab_object = deutan(lab_obj),
    linear_false = deutan(c("#FF0000", "#800080", "#FFA500"), linear = FALSE),
    examples = deutan(examples),
    bulk = deutan(sprintf("#%02X%02X%02X", 0:255, 255:0, (0:255 + 17) %% 256))
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
    '{"default":%s,"severity":%s,"zero":%s,"named":%s,',
    '"colors":%s,"palette":%s,"rgb_matrix":%s,',
    '"srgb_object":%s,"lab_object":%s,"linear_false":%s,',
    '"examples":%s,"bulk":%s,"median_ms":%.17g}\n'
  ),
  json_vec(unname(value$default)),
  json_vec(unname(value$severity)),
  json_vec(unname(value$zero)),
  json_vec(unname(value$named)),
  json_vec(unname(value$colors)),
  json_vec(unname(value$palette)),
  json_mat(value$rgb_matrix),
  json_color(value$srgb_object),
  json_color(value$lab_object),
  json_vec(unname(value$linear_false)),
  json_vec(unname(value$examples)),
  json_vec(unname(value$bulk)),
  median(elapsed) * 1000
))
