suppressPackageStartupMessages(library(colorspace))
stopifnot(identical(packageDescription("colorspace")$Version, "2.1-4"))

args <- commandArgs(trailingOnly = FALSE)
f_pos <- which(args == "-f")
script <- if (length(f_pos)) args[f_pos[1L] + 1L] else sub("^--file=", "", grep("^--file=", args, value = TRUE)[1L])
out_dir <- file.path(normalizePath(file.path(dirname(script), "..")), "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

json_num <- function(x) if (is.na(x)) "null" else sprintf("%.17g", as.numeric(x))
json_str <- function(s) if (is.na(s)) "null" else paste0('"', s, '"')
json_vec <- function(x) {
  f <- if (is.character(x)) json_str else json_num
  paste0("[", paste(vapply(x, f, ""), collapse = ","), "]")
}

cl <- c("#CDE4F3", "#E7F3D3", "#F7F0C7", "#EFCFE5", "#D0D1E7")
hexes <- c("#FF0000", "#00FF0080", "#336699", "#AABBCCDD")

one <- function() {
  list(
    default = darken(cl, 0.15),
    hcl = darken(cl, 0.15, space = "HCL"),
    hls = darken(cl, 0.15, space = "HLS"),
    deep = darken(cl, 0.3),
    absolute = darken(hexes, 0.2, method = "absolute"),
    zero = darken(c("#112233", "#445566"), c(0.2, 0)),
    recycle = darken("#112233", c(0.1, 0.2, 0.3)),
    negative = darken(cl, -0.1),
    named = darken(c(red = "#FF0000", blue = "#0000FF")),
    palette = darken(1:3, 0.25),
    no_fixup = darken(c("#FF0000", "#010101"), 0.5, fixup = FALSE),
    bulk = darken(
      sprintf("#%02X%02X%02X", 0:255, 255:0, (0:255 + 17) %% 256),
      0.12
    )
  )
}

time_median <- function(f) {
  f()
  elapsed <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    f()
    elapsed[[i]] <- as.numeric(Sys.time()) - t0
  }
  median(elapsed) * 1000
}

value <- one()
median_ms <- time_median(one)

parts <- vapply(names(value), function(k) {
  paste0('"', k, '":', json_vec(unname(value[[k]])))
}, "")
cat("{", paste(parts, collapse = ","), ',"median_ms":', sprintf("%.17g", median_ms), "}\n", sep = "")

sink(file.path(out_dir, "darken-r.txt"))
cat(darken(cl, 0.15), sep = "\n")
cat("\n")
sink()
