.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(coda))
if (packageDescription("coda")$Version != "0.19-4.1") stop("expected coda 0.19-4.1")
options(warn = -1)

n <- 80L
i <- seq_len(n)
alpha <- sin(i / 3) + 0.2 * cos(i)
beta <- cos(i / 5) + 0.01 * i
chain <- mcmc(cbind(alpha = alpha, beta = beta), start = 11, thin = 2)
obj <- mcmc.list(chain)
names(obj) <- "north"

# The numbers matplot receives: iterations, then each panel column-major.
plotted <- function(obj) {
  caps <- list()
  trace(matplot, tracer = quote({
    caps <- get("caps", envir = .GlobalEnv)
    caps[[length(caps) + 1]] <- list(
      x = as.numeric(x),
      y = as.numeric(as.matrix(y))
    )
    assign("caps", caps, envir = .GlobalEnv)
  }), print = FALSE, where = asNamespace("graphics"))
  on.exit(untrace(matplot, where = asNamespace("graphics")), add = TRUE)
  assign("caps", list(), envir = .GlobalEnv)
  pdf(nullfile())
  on.exit(dev.off(), add = TRUE)
  cumuplot(obj, ask = FALSE)
  caps <- get("caps", envir = .GlobalEnv)
  c(caps[[1]]$x, unlist(lapply(caps, `[[`, "y"), use.names = FALSE))
}

value <- plotted(obj)

dir.create("docs/output", recursive = TRUE, showWarnings = FALSE)
svg("docs/output/cumuplot-r.svg", width = 7, height = 5)
cumuplot(obj, ask = FALSE)
dev.off()

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  pdf(nullfile())
  cumuplot(obj, ask = FALSE)
  dev.off()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

parts <- sprintf("%.17g", value)
out <- sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(parts, collapse = ","),
  median(elapsed) * 1000
)
writeLines(out, con = "proof/cumuplot-r.txt")
