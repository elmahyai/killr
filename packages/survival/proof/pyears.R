suppressPackageStartupMessages(library(survival))

hearta <- by(heart, heart$id, function(x) x[x$stop == max(x$stop), ])
hearta <- do.call("rbind", hearta)

serialize_pyears <- function(fit) {
  c(
    sprintf("%.17g", fit$pyears),
    sprintf("%.17g", fit$n),
    sprintf("%.17g", fit$event),
    sprintf("%.17g", fit$offtable),
    sprintf("%.17g", fit$observations)
  )
}

one <- function() {
  fit <- pyears(
    Surv(stop / 365.25, event) ~ cut(age + 48, c(0, 50, 60, 70, 100)) + surgery,
    data = hearta,
    scale = 1
  )
  serialize_pyears(fit)
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
