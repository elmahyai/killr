suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

fmt <- function(v) {
  if (is.null(v)) return("NULL")
  if (is.character(v)) return(paste(v, collapse = ","))
  if (is.logical(v)) return(paste(toupper(as.character(v)), collapse = ","))
  paste(vapply(as.vector(v), function(z) if (is.na(z)) "NA" else sprintf("%.17g", z), ""),
        collapse = ",")
}

one <- function() {
  out <- character(0)
  add <- function(label, value) out <<- c(out, paste0(label, "|", value))

  add("names", paste(names(survreg.distributions), collapse = ","))

  x_grid <- c(-2, -0.5, 0, 0.7, 1.5)
  p_grid <- c(0.1, 0.25, 0.5, 0.75, 0.9)
  xi <- c(1, 2, 3, 5, 8)
  wi <- c(1, 1, 2, 1, 1)
  yy <- cbind(c(1, 2, 1.5, 1, 0.5), c(1, 2, 1.5, 2.5, 1.5), c(1, 0, 2, 3, 3))
  tr <- c(0.5, 2)
  itr <- c(-0.5, 0.7)

  for (k in names(survreg.distributions)) {
    d <- survreg.distributions[[k]]
    isT <- identical(k, "t")
    prm <- if (isT) 4 else NULL

    add(paste0(k, ".name"), fmt(d$name))
    add(paste0(k, ".dist"), fmt(d$dist))
    add(paste0(k, ".scale"), fmt(d$scale))
    add(paste0(k, ".parms"), fmt(d$parms))
    add(paste0(k, ".variance"),
        if (is.null(d$variance)) "NULL" else fmt(d$variance(4)))
    add(paste0(k, ".init"),
        if (is.null(d$init)) "NULL" else
          fmt(if (isT) d$init(xi, wi, 4) else d$init(xi, wi)))
    if (is.null(d$deviance)) {
      add(paste0(k, ".center"), "NULL")
      add(paste0(k, ".loglik"), "NULL")
    } else {
      r <- d$deviance(yy, 2, prm)
      add(paste0(k, ".center"), fmt(r$center))
      add(paste0(k, ".loglik"), fmt(r$loglik))
    }
    add(paste0(k, ".density"),
        if (is.null(d$density)) "NULL" else fmt(t(d$density(x_grid, prm))))
    add(paste0(k, ".quantile"),
        if (is.null(d$quantile)) "NULL" else fmt(d$quantile(p_grid, prm)))
    add(paste0(k, ".trans"), if (is.null(d$trans)) "NULL" else fmt(d$trans(tr)))
    add(paste0(k, ".dtrans"), if (is.null(d$dtrans)) "NULL" else fmt(d$dtrans(tr)))
    add(paste0(k, ".itrans"), if (is.null(d$itrans)) "NULL" else fmt(d$itrans(itr)))
    add(paste0(k, ".survregDtest"), if (survregDtest(d)) "TRUE" else "FALSE")
  }
  out
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(value, collapse = "\n"), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
