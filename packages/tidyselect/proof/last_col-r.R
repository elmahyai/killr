suppressPackageStartupMessages(library(tidyselect))
stopifnot(as.character(packageVersion("tidyselect")) == "1.2.1")

vars <- paste0("v", seq_len(10000))
one <- function() {
  last_col(5, vars)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

names <- c("mpg", "cyl", "disp", "hp", "drat", "wt", "qsec", "vs", "am", "gear", "carb")
example <- last_col(5, names)
out <- "/home/ahmed/killr_projects/killr/packages/tidyselect/docs/output/last_col-r.txt"
dir.create(dirname(out), recursive = TRUE, showWarnings = FALSE)
writeLines(
  paste0(
    "last_col(5, c(\"mpg\", \"cyl\", \"disp\", \"hp\", \"drat\", \"wt\", \"qsec\", \"vs\", \"am\", \"gear\", \"carb\")) returns ",
    example,
    "."
  ),
  out
)

cat("VERSION ", as.character(packageVersion("tidyselect")), "\n", sep = "")
cat("VALUE ", value, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
