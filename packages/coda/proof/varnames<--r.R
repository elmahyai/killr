.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(coda))
if (packageDescription("coda")$Version != "0.19-4.1") stop("expected coda 0.19-4.1")
options(warn = -1)

root <- normalizePath(".", winslash = "/", mustWork = FALSE)

encode_names <- function(v) {
  if (is.null(v)) {
    return(0)
  }
  out <- c(length(v), nchar(v))
  for (nm in v) {
    out <- c(out, as.numeric(charToRaw(nm)))
  }
  out
}

one <- function() {
  n <- 2000L
  i <- seq_len(n)
  x <- cbind(
    sin(i / 3) + 0.2 * cos(i),
    cos(i / 5) + 0.01 * i,
    rep(2, n)
  )
  m <- mcmc(x)
  
  # Test varnames<- assignment on single mcmc object
  varnames(m) <- c("theta1", "theta2", "theta3")
  names_after_set <- varnames(m)
  
  # Create mcmc.list with compatible chains
  y <- cbind(
    sin(i / 4) + 0.15 * cos(i / 2),
    cos(i / 6) + 0.005 * i,
    rep(1, n)
  )
  m2 <- mcmc(y)
  
  # Set names on m2 to match m before creating list
  varnames(m2) <- c("theta1", "theta2", "theta3")
  ml <- mcmc.list(m, m2)
  
  # Now test varnames<- on the mcmc.list
  varnames(ml) <- c("alpha", "beta", "gamma")
  names_list <- varnames(ml)
  
  c(
    encode_names(names_after_set),
    encode_names(names_list),
    encode_names(varnames(ml[[1]])),
    encode_names(varnames(ml[[2]]))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
parts <- sprintf("%.17g", value)
out <- sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(parts, collapse = ","),
  median(elapsed) * 1000
)
writeLines(out, con = file.path(root, "varnames<--r.txt"))
