# Proof: R mclust::mclustLoglik on fixed inputs. Run from packages/mclust.
source("proof/bic_proof_common.R")

A <- bic_obj(1:9, 1:10, models14[1:10], 150, 4, "A")
B <- bic_obj(2:10, 5:14, models14[5:14], 150, 4, "B")
N <- bic_obj(0:3, 1:3, c("EII", "VVV", "EEE"), 200, 2, "N", noise = TRUE)
O <- bic_obj(1:4, 1:3, c("E", "V", "X"), 60, 1, "O")

cases <- list(
  list(id = "L1-A", x = A),
  list(id = "L2-B", x = B),
  list(id = "L3-noise-G0", x = N),
  list(id = "L4-d1-X-alias", x = O)
)

run_all <- function() lapply(cases, function(cs) mclustLoglik(cs$x))

res <- run_all()  # one untimed call, used for the records

rec <- character(0)
for (i in seq_along(cases)) {
  rec <- c(rec, matrix_record(cases[[i]]$id, res[[i]]))
}

ms <- time_median_ms(run_all)
write_record("mclustLoglik", rec, ms)
cat("R mclustLoglik median ms:", ms, "\n")
