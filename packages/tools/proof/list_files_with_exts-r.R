suppressPackageStartupMessages(library(tools))

one <- function() {
  dir <- tempfile()
  dir.create(dir)
  writeLines("z", file.path(dir, "a.R"))
  writeLines("y", file.path(dir, "b.r"))
  writeLines("n", file.path(dir, "notes.txt"))
  writeLines("h", file.path(dir, ".hidden.R"))
  writeLines("d", file.path(dir, "1demo.R"))
  dir.create(file.path(dir, "unix"))
  writeLines("o", file.path(dir, "unix", "os.R"))
  paste0(paste(list_files_with_exts(dir, "R", full.names=FALSE), collapse="|"), "\n",
         paste(list_files_with_exts(dir, c("R","r"), all.files=TRUE, full.names=FALSE), collapse="|"), "\n",
         paste(list_files_with_exts(dir, "txt", full.names=FALSE), collapse="|"), "\n")
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(value, sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
