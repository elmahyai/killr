pkg <- "../../../cran/contrib/DEoptimR_1.2-2.tar.gz"
td <- tempfile(); dir.create(td)
untar(pkg, exdir=td)
source(file.path(td, "DEoptimR/R/JDEoptim.R"))
source(file.path(td, "DEoptimR/R/NCDEoptim.R"))
source(file.path(td, "DEoptimR/R/SPJDEoptim.R"))
out <- "../docs/output/r_values.txt"
dir.create("../docs/output", recursive=TRUE, showWarnings=FALSE)
run <- function(name, f) {
  z <- f()
  tm <- numeric(20)
  for (i in seq_len(20)) { a <- Sys.time(); f(); tm[i] <- as.numeric(Sys.time()-a) }
  write(paste(name, paste(format(as.numeric(unlist(z)), digits=17), collapse=","),
              sprintf("median_ms=%.6g", median(tm)*1000)),
        out, append=TRUE)
  invisible(z)
}
file.remove(out)
set.seed(1)
run("JDEoptim", function() JDEoptim(c(-2,-2), c(2,2), function(x) sum(x^2),
  NP=0, maxiter=0, add_to_init_pop=matrix(c(1,2,-1,.5,0,1,1,-2),2,4), details=TRUE))
run("SPJDEoptim", function() SPJDEoptim(c(-2,-2), c(2,2), function(x) sum(x^2),
  NP=0, maxiter=0, add_to_init_pop=matrix(c(1,2,-1,.5,0,1,1,-2),2,4),
  sequential_eval="both", details=TRUE))
run("NCDEoptim", function() NCDEoptim(c(-2,-2), c(2,2), function(x) sum(x^2),
  NP=0, nbngbrsl=3, nbngbrsu=3, maxiter=0,
  add_to_init_pop=matrix(c(1,2,-1,.5,0,1,1,-2),2,4)))
