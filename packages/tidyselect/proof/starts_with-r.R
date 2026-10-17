suppressPackageStartupMessages(library(tidyselect))
stopifnot(as.character(packageVersion("tidyselect")) == "1.2.1")

vars <- paste0("v", seq_len(10000))
match <- c("V1", "v2", "zz", "V99")
one <- function() {
  starts_with(match, vars = vars)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

example <- starts_with(
  c("Petal", "Sepal"),
  vars = c("Sepal.Length", "Sepal.Width", "Petal.Length", "Petal.Width", "Species")
)
out <- "/home/ahmed/killr_projects/killr/packages/tidyselect/docs/output/starts_with-r.txt"
dir.create(dirname(out), recursive = TRUE, showWarnings = FALSE)
writeLines(
  paste0(
    "starts_with(c(\"Petal\", \"Sepal\"), vars = c(\"Sepal.Length\", \"Sepal.Width\", \"Petal.Length\", \"Petal.Width\", \"Species\")) returns ",
    paste(example, collapse = ", "),
    "."
  ),
  out
)

cat("VERSION ", as.character(packageVersion("tidyselect")), "\n", sep = "")
cat("VALUE ", paste(value, collapse = ","), "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
