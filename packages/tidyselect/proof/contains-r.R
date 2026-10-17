suppressPackageStartupMessages(library(tidyselect))
stopifnot(as.character(packageVersion("tidyselect")) == "1.2.1")

vars <- paste0("Var", seq_len(10000))
one <- function() {
  contains(c("00", "99"), vars = vars)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

iris <- c("Sepal.Length", "Sepal.Width", "Petal.Length", "Petal.Width", "Species")
example <- contains("al", vars = iris)
out <- "/home/ahmed/killr_projects/killr/packages/tidyselect/docs/output/contains-r.txt"
dir.create(dirname(out), recursive = TRUE, showWarnings = FALSE)
writeLines(
  paste0(
    "contains(\"al\", vars = c(\"Sepal.Length\", \"Sepal.Width\", \"Petal.Length\", \"Petal.Width\", \"Species\")) returns ",
    paste(example, collapse = ", "),
    "."
  ),
  out
)

cat("VERSION ", as.character(packageVersion("tidyselect")), "\n", sep = "")
cat("VALUE ", paste(value, collapse = ","), "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
