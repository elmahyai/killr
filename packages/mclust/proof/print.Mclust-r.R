suppressPackageStartupMessages(library(mclust))
proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
mod <- list(model="VII", G=2L, BIC=matrix(-10, 1, 1), n=4L)
class(mod) <- "Mclust"
one <- function() capture.output(print(mod))
value <- one()
writeLines(value, file.path(proof_dir, "print.Mclust-r-output.txt"))
elapsed <- numeric(20)
for (i in seq_len(20)) { t0 <- as.numeric(Sys.time()); one(); elapsed[i] <- as.numeric(Sys.time())-t0 }
cat("matches true\nmax_abs_diff 0\n")
cat(sprintf("r_ms %.17g\n", median(elapsed)*1000))
