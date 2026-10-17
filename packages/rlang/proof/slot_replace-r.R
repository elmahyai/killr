.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(rlang))
.Person <- setClass("Person", slots = c(name = "character", species = "character"))
one <- function() {
  x <- structure(NA, test = 42, tag = "x")
  x %@% "test" <- 99
  x %@% "new" <- "added"
  x %@% tag <- NULL
  fievel <- .Person(name = "Fievel", species = "mouse")
  fievel %@% name <- "Updated"
  fievel %@% species <- "rat"
  paste(
    as.character(x %@% "test"),
    if (is.null(x %@% "new")) "NULL" else x %@% "new",
    if (is.null(x %@% "tag")) "NULL" else "notnull",
    fievel@name,
    fievel@species,
    sep = " "
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
shown <- enc2utf8(paste(as.character(value), collapse = "|"))
shown <- gsub("\n", " / ", shown, fixed = TRUE)
cat("VALUE ", shown, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
