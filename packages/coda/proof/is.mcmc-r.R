.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(coda))
if (packageDescription("coda")$Version != "0.19-4.1") stop("expected coda 0.19-4.1")
options(warn = -1)

one <- function() {
  n <- 2000L
  i <- seq_len(n)
  x <- cbind(
    sin(i / 3) + 0.2 * cos(i),
    cos(i / 5) + 0.01 * i,
    rep(2, n)
  )
  m <- mcmc(x)
  v <- mcmc(sin(i / 7))
  ml <- mcmc.list(m, mcmc(x))
  obsolete <- array(seq_len(24), dim = c(2L, 3L, 4L))
  class(obsolete) <- "mcmc"
  msg <- tryCatch(is.mcmc(obsolete), error = function(e) conditionMessage(e))
  flags <- as.numeric(c(
    is.mcmc(m),
    is.mcmc(v),
    is.mcmc(x),
    is.mcmc(ml),
    is.mcmc(NULL),
    is.mcmc(list(m))
  ))
  c(flags, nchar(msg), utf8ToInt(msg))
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
writeLines(out, con = "proof/is.mcmc-r.txt")

n <- 2000L
i <- seq_len(n)
x <- cbind(
  sin(i / 3) + 0.2 * cos(i),
  cos(i / 5) + 0.01 * i,
  rep(2, n)
)
m <- mcmc(x)
v <- mcmc(sin(i / 7))
ml <- mcmc.list(m, mcmc(x))
obsolete <- array(seq_len(24), dim = c(2L, 3L, 4L))
class(obsolete) <- "mcmc"
msg <- tryCatch(is.mcmc(obsolete), error = function(e) conditionMessage(e))
example <- paste0(
  "mcmc matrix: ", is.mcmc(m), "\n",
  "mcmc vector: ", is.mcmc(v), "\n",
  "numeric matrix: ", is.mcmc(x), "\n",
  "mcmc.list: ", is.mcmc(ml), "\n",
  "NULL: ", is.mcmc(NULL), "\n",
  "list: ", is.mcmc(list(m)), "\n",
  msg, "\n"
)
cat(example, file = "docs/output/is.mcmc-r.txt")
