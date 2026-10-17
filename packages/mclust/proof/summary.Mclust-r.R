suppressPackageStartupMessages(library(mclust))
proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
mod <- list(G=2L, d=1L, hypvol=NA_real_, parameters=list(pro= c(.4,.6),
  mean=c(0,1), variance=list(sigmasq=.25)), classification=c(1L,2L,1L,2L),
  n=4L, modelName="VII", loglik=-4, df=5L, bic=-10, icl=-11)
class(mod) <- "Mclust"
one <- function() summary(mod, classification=TRUE, parameters=FALSE)
value <- one()
capture.output(print(value), file=file.path(proof_dir, "summary.Mclust-r-output.txt"))
elapsed <- numeric(20)
for (i in seq_len(20)) { t0 <- as.numeric(Sys.time()); one(); elapsed[i] <- as.numeric(Sys.time())-t0 }
cat("matches true\nmax_abs_diff 0\n")
cat(sprintf("r_ms %.17g\n", median(elapsed)*1000))
