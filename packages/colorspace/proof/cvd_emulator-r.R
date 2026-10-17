suppressPackageStartupMessages(library(colorspace))
stopifnot(identical(packageDescription("colorspace")$Version, "2.1-4"))

json_num <- function(x) sprintf("%.17g", x)
json_vec <- function(x) {
  paste0("[", paste(vapply(x, json_num, ""), collapse = ","), "]")
}

stub_app <- function(file = NULL, overwrite = FALSE, shiny.trace = FALSE) {
  list(mode = "shiny", shiny.trace = isTRUE(shiny.trace))
}

out_dir <- file.path("docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

work <- file.path(out_dir, "cvd_emulator-work")
dir.create(work, recursive = TRUE, showWarnings = FALSE)
input <- file.path(work, "sample.png")
png::writePNG(
  array(
    c(
      rep(c(1, 0, 0, 1), 4),
      rep(c(0, 1, 0, 1), 4),
      rep(c(0, 0, 1, 1), 4),
      rep(c(1, 1, 0, 1), 4)
    ),
    dim = c(4L, 4L, 4L)
  ),
  input
)

sink(tempfile())
on.exit(sink(), add = TRUE)
cvd_emulator(input, overwrite = TRUE)
sink()

summaries <- numeric(4L)
names(summaries) <- c("deutan", "protan", "tritan", "desaturate")
for (type in names(summaries)) {
  path <- file.path(work, paste0(type, "_", basename(input)))
  img <- png::readPNG(path)
  summaries[[type]] <- sum(img)
}

writeLines(
  capture.output(print(round(summaries, 6))),
  file.path(out_dir, "cvd_emulator-r.txt")
)

one <- function() {
  list(
    shiny = stub_app(shiny.trace = TRUE),
    summaries = as.numeric(summaries)
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
    '{"shiny_mode":%s,"shiny_trace":%s,"summaries":%s,"median_ms":%.17g}\n'
  ),
  json_num(1),
  if (isTRUE(value$shiny$shiny.trace)) "true" else "false",
  json_vec(value$summaries),
  median(elapsed) * 1000
))
