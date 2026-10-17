library(SQUAREM)
fixed <- function(x, target, rate) target + rate * (x - target)
objective <- function(x, target, rate) sum((x - target)^2)
x <- c(3, -2, 5)
control <- list(tol=1e-10, maxiter=500, method=3)
cases <- list(
  squarem = function() squarem(x, fixed, objective, target=c(1, 2, 3), rate=.92,
                                control=control),
  fpiter = function() fpiter(x, fixed, objective, target=c(1, 2, 3), rate=.92,
                              control=list(tol=1e-10, maxiter=500))
)
for (nm in names(cases)) {
  invisible(cases[[nm]]())
  t <- numeric(20)
  for (i in seq_len(20)) {
    a <- Sys.time(); z <- cases[[nm]](); t[[i]] <- as.numeric(difftime(Sys.time(), a, units="secs"))
  }
  cat(nm, paste(formatC(z$par, digits=17, format="fg", flag="#"), collapse=","), z$fpevals,
      z$objfevals, as.numeric(z$value.objfn), median(t) * 1000, "\n")
}
