suppressPackageStartupMessages(library(colorspace))
stopifnot(identical(packageDescription("colorspace")$Version, "2.1-4"))

json_num <- function(x) sprintf("%.17g", x)
json_str <- function(s) {
  s <- enc2utf8(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub("\"", "\\\"", s, fixed = TRUE)
  paste0('"', s, '"')
}
json_names <- function(nm) {
  if (is.null(nm)) return("null")
  paste0("[", paste(vapply(nm, json_str, ""), collapse = ","), "]")
}
json_mat <- function(m) {
  if (length(m) == 0) return("[]")
  parts <- character(nrow(m))
  for (i in seq_len(nrow(m))) {
    parts[[i]] <- paste0(
      "[", paste(vapply(m[i, ], json_num, ""), collapse = ","), "]"
    )
  }
  paste0("[", paste(parts, collapse = ","), "]")
}
json_color <- function(obj) {
  cols <- colnames(obj@coords)
  if (is.null(cols)) cols <- character(0)
  sprintf(
    '{"space":%s,"names":%s,"columns":[%s],"coords":%s}',
    json_str(class(obj)[[1L]]),
    json_names(rownames(obj@coords)),
    paste(vapply(cols, json_str, ""), collapse = ","),
    json_mat(obj@coords)
  )
}

one <- function() {
  red <- sRGB(1, 0, 0)
  green <- sRGB(0, 1, 0)
  bulk_a <- sRGB(
    seq(0, 1, length.out = 256),
    rep(0, 256),
    seq(1, 0, length.out = 256)
  )
  bulk_b <- sRGB(
    rep(0, 256),
    seq(0, 1, length.out = 256),
    seq(0, 1, length.out = 256)
  )
  suppressWarnings({
    list(
      example = mixcolor(0.5, red, green),
      rgb = mixcolor(0.25, RGB(1, 0, 0), RGB(0, 0, 1)),
      lab = mixcolor(0.5, LAB(50, 50, 0), LAB(50, -50, 0)),
      hsv = mixcolor(0.5, HSV(0, 1, 1), HSV(120, 1, 1)),
      polarluv = mixcolor(
        0.3,
        polarLUV(50, 80, 0),
        polarLUV(50, 80, 180)
      ),
      where_xyz = mixcolor(0.5, red, green, where = "XYZ"),
      where_luv = mixcolor(0.5, LUV(50, 0, 0), LUV(50, 10, -10)),
      recycle_alpha = mixcolor(c(0.25, 0.5, 0.75), red, green),
      recycle_colors = mixcolor(
        0.5,
        sRGB(c(1, 0, 0), c(0, 0, 1), c(0, 0, 0)),
        green
      ),
      bulk = mixcolor(seq(0, 1, length.out = 256), bulk_a, bulk_b)
    )
  })
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
    '{"example":%s,"rgb":%s,"lab":%s,"hsv":%s,"polarluv":%s,',
    '"where_xyz":%s,"where_luv":%s,"recycle_alpha":%s,"recycle_colors":%s,',
    '"bulk":%s,"median_ms":%.17g}\n'
  ),
  json_color(value$example),
  json_color(value$rgb),
  json_color(value$lab),
  json_color(value$hsv),
  json_color(value$polarluv),
  json_color(value$where_xyz),
  json_color(value$where_luv),
  json_color(value$recycle_alpha),
  json_color(value$recycle_colors),
  json_color(value$bulk),
  median(elapsed) * 1000
))
