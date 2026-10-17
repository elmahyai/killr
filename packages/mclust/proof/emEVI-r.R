suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
n <- 60L; p <- 3L
x <- matrix(0, n, p)
for (i in 1:n) for (j in 1:p) x[i, j] <- sin(.37*i + 1.3*j) + .4*cos(.11*i*j) + .05*i/n*j
mu <- matrix(c(.1, -.2, .3, .5, .4, -.1), p, 2)
rc <- function(o) { a <- attr(o, "returnCode"); if (is.null(a)) o$returnCode else a }
flat <- function(o, keys) {
  v <- o$parameters$variance
  c(rc(o), as.numeric(o$parameters$pro), as.numeric(o$parameters$mean),
    unlist(lapply(keys, function(k) as.numeric(v[[k]]))), as.numeric(o$z),
    if (!is.null(o$loglik)) as.numeric(o$loglik))
}
pars <- function(pro, Vinv = NULL) {
  a <- list(pro = pro, mean = mu,
            variance = list(scale = .9, shape = matrix(c(1.5, .8, 1.1, .6, 1.4, .9), p, 2)))
  if (!is.null(Vinv)) a$Vinv <- Vinv
  a
}
one <- function() c(flat(emEVI(x, pars(c(.4, .6))), c("scale", "shape")),
                    flat(emEVI(x, pars(c(.3, .45, .25), .15)), c("scale", "shape")))
value <- one(); elapsed <- numeric(20)
for (i in seq_len(20)) { t0 <- as.numeric(Sys.time()); one(); elapsed[i] <- as.numeric(Sys.time()) - t0 }
cat(sprintf("%.17g\n", value), sep = "")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
