suppressPackageStartupMessages(library(tidyselect))
stopifnot(as.character(packageVersion("tidyselect")) == "1.2.1")

vars <- paste0("v", seq_len(10000))
wanted <- paste0("v", seq(10000, 1))
poke_vars(vars)
one <- function() {
  all_of(wanted)
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

iris <- c("Sepal.Length", "Sepal.Width", "Petal.Length", "Petal.Width", "Species")
example <- with_vars(iris, all_of(c("Sepal.Length", "Sepal.Width")))
out <- "/home/ahmed/killr_projects/killr/packages/tidyselect/docs/output/all_of-r.txt"
dir.create(dirname(out), recursive = TRUE, showWarnings = FALSE)
writeLines(
  paste0(
    "with_vars(c(\"Sepal.Length\", \"Sepal.Width\", \"Petal.Length\", \"Petal.Width\", \"Species\"), all_of(c(\"Sepal.Length\", \"Sepal.Width\"))) returns ",
    paste(example, collapse = ", "),
    "."
  ),
  out
)

cat("VERSION ", as.character(packageVersion("tidyselect")), "\n", sep = "")
cat("VALUE ", paste(value, collapse = ","), "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
