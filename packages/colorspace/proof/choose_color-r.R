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

ns <- asNamespace("colorspace")
stub_picker <- function(shiny.trace = FALSE) {
  list(color = "#336699", shiny.trace = isTRUE(shiny.trace))
}
unlockBinding("hcl_color_picker", ns)
assign("hcl_color_picker", stub_picker, ns)
lockBinding("hcl_color_picker", ns)

out_dir <- file.path("docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
writeLines("#336699", con = file.path(out_dir, "choose_color-r.txt"))

one <- function() {
  list(
    default = choose_color(),
    traced = choose_color(shiny.trace = TRUE)
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
    '{"default_color":%s,"default_trace":%s,',
    '"traced_color":%s,"traced_trace":%s,"median_ms":%.17g}\n'
  ),
  json_str(value$default$color),
  if (isTRUE(value$default$shiny.trace)) "true" else "false",
  json_str(value$traced$color),
  if (isTRUE(value$traced$shiny.trace)) "true" else "false",
  median(elapsed) * 1000
))
