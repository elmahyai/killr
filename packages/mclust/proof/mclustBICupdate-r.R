# Proof: R mclust::mclustBICupdate on fixed inputs. Run from packages/mclust.
source("proof/bic_proof_common.R")

A  <- bic_obj(1:9, 1:10, models14[1:10], 150, 4, "A")
A2 <- bic_obj(1:9, 1:10, models14[1:10], 150, 4, "A2")   # same values, tie
B  <- bic_obj(2:10, 5:14, models14[5:14], 150, 4, "B")
C  <- bic_obj(1:9, 11:14, models14[11:14], 150, 4, "C", cls = "mclustICL")

cases <- list(
  list(id = "U1-A-B",        f = function() mclustBICupdate(A, B)),
  list(id = "U2-A-B-C",      f = function() mclustBICupdate(A, B, C)),
  list(id = "U3-A-NULL",     f = function() mclustBICupdate(A, NULL)),
  list(id = "U4-NULL-B",     f = function() mclustBICupdate(NULL, B)),
  list(id = "U5-A-A2-tie",   f = function() mclustBICupdate(A, A2)),
  list(id = "U6-A2-A-tie",   f = function() mclustBICupdate(A2, A)),
  list(id = "U7-B-A",        f = function() mclustBICupdate(B, A)),
  list(id = "U8-C-A-B",      f = function() mclustBICupdate(C, A, B))
)

run_all <- function() lapply(cases, function(cs) cs$f())

res <- run_all()  # one untimed call, used for the records

rec <- character(0)
for (i in seq_along(cases)) {
  rec <- c(rec, matrix_record(cases[[i]]$id, res[[i]]))
}

ms <- time_median_ms(run_all)
write_record("mclustBICupdate", rec, ms)
cat("R mclustBICupdate median ms:", ms, "\n")
