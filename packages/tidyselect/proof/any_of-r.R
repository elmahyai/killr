suppressPackageStartupMessages(library(tidyselect))
stopifnot(as.character(packageVersion("tidyselect")) == "1.2.1")

vars <- paste0("v", seq_len(10000))
rev <- paste0("v", seq(10000, 1))
wanted <- c(rev, rev, paste0("missing", seq_len(100)))
poke_vars(vars)
one <- function() {
  any_of(wanted)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

iris <- c("Sepal.Length", "Sepal.Width", "Petal.Length", "Petal.Width", "Species")
example <- with_vars(iris, any_of(c("Sepal.Length", "not_there", "Sepal.Width")))
out <- "/home/ahmed/killr_projects/killr/packages/tidyselect/docs/output/any_of-r.txt"
dir.create(dirname(out), recursive = TRUE, showWarnings = FALSE)
writeLines(
  paste0(
    "with_vars(c(\"Sepal.Length\", \"Sepal.Width\", \"Petal.Length\", \"Petal.Width\", \"Species\"), any_of(c(\"Sepal.Length\", \"not_there\", \"Sepal.Width\"))) returns ",
    paste(example, collapse = ", "),
    "."
  ),
  out
)

cat("VERSION ", as.character(packageVersion("tidyselect")), "\n", sep = "")
cat("VALUE ", paste(value, collapse = ","), "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
