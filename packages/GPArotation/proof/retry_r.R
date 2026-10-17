A <- matrix(c(.8,.1,.2,.2,.7,.1,.1,.2,.9,.6,.2,.3,.2,.8,.4),5,3,byrow=TRUE)
seed <- 20261017
if (!requireNamespace("GPArotation", quietly=TRUE)) stop("Install GPArotation 2026.8-2 before running proof")
if (as.character(packageVersion("GPArotation")) != "2026.8.2") stop("GPArotation must be 2026.8-2")
# Random.Start is seeded before each call, so the untimed and timed calls draw the same matrix.
prep <- function(nm) if (nm == "Random.Start") set.seed(seed)
cases <- list(
  Random.Start=function() GPArotation:::Random.Start(3),
  oblimax=function() GPArotation:::oblimax(A,maxit=200),
  bifactorQ=function() GPArotation:::bifactorQ(A,maxit=200),
  lpT=function() GPArotation:::lpT(A,maxit=200),
  lpQ=function() GPArotation:::lpQ(A,maxit=200),
  GPForth.lp=function() GPArotation:::GPForth.lp(A,maxit=200),
  GPFoblq.lp=function() GPArotation:::GPFoblq.lp(A,maxit=200)
)
vals <- list(); times <- list()
for (nm in names(cases)) {
  prep(nm)
  r <- cases[[nm]]()  # untimed call
  if (nm == "Random.Start") {
    vals[[nm]] <- as.numeric(r)
  } else {
    vals[[nm]] <- c(as.numeric(r$loadings), r$Table[nrow(r$Table), 2])
  }
  z <- numeric(20)
  for (i in 1:20) {
    prep(nm)
    t0 <- Sys.time()
    cases[[nm]]()
    z[i] <- as.numeric(difftime(Sys.time(), t0, units="secs")) * 1000
  }
  times[[nm]] <- median(z)
  cat(nm, sprintf(" r_ms=%.6f\n", median(z)))
}
rows <- vapply(names(vals), function(nm)
  paste(c(nm, sprintf("%.10f", times[[nm]]), sprintf("%.17g", vals[[nm]])), collapse=","), character(1))
writeLines(rows, "packages/GPArotation/docs/output/retry_r.csv")
