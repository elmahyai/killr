library(utils)

if (!methods::isClass("TestS4AtNames", where = .GlobalEnv)) {
  methods::setClass(
    "TestS4AtNames",
    slots = c(a = "numeric", b = "character"),
    where = .GlobalEnv
  )
}
obj <- methods::new("TestS4AtNames", a = 1, b = "x")

one <- function() {
  paste(.AtNames(obj, ""), collapse = ",")
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(value, "\n", sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
