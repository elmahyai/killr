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

ns <- asNamespace("colorspace")
stub_tcl <- function(pal, n = 7L, parent = NULL, ...) pal(n)
stub_shiny <- function(pal, n = 7L, ...) pal(n)
unlockBinding("choose_palette_tcltk", ns)
assign("choose_palette_tcltk", stub_tcl, ns)
lockBinding("choose_palette_tcltk", ns)
unlockBinding("choose_palette_shiny", ns)
assign("choose_palette_shiny", stub_shiny, ns)
lockBinding("choose_palette_shiny", ns)

out_dir <- file.path("docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
pal_fn <- diverging_hcl
writeLines(pal_fn(7L), con = file.path(out_dir, "choose_palette-r.txt"))

one <- function() {
  list(
    default_tcl = choose_palette(gui = "tcltk"),
    seq_shiny = choose_palette(sequential_hcl, 5L, gui = "shiny"),
    rainbow_tcl = choose_palette(rainbow_hcl, 6L, gui = "tcltk"),
    custom_n = choose_palette(diverging_hcl, 11L, gui = "shiny")
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
    '{"default_tcl":%s,"seq_shiny":%s,"rainbow_tcl":%s,"custom_n":%s,',
    '"median_ms":%.17g}\n'
  ),
  json_vec(unname(value$default_tcl)),
  json_vec(unname(value$seq_shiny)),
  json_vec(unname(value$rainbow_tcl)),
  json_vec(unname(value$custom_n)),
  median(elapsed) * 1000
))
