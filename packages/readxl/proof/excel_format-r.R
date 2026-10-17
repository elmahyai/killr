.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(readxl))
one <- function() {
  files <- c("a.xlsx", "b.xls", "c.png", "/etc/hostname", readxl_example("clippy.xlsx"), readxl_example("deaths.xls"))
paste(ifelse(is.na(excel_format(files)), "NA", excel_format(files)), collapse = "|")
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat("VALUE\n")
cat(value, "\n", sep = "")
cat("<<<END>>>\n")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
