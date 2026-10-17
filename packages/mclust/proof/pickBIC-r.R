# Proof: R mclust::pickBIC on fixed inputs. Run from packages/mclust.
source("proof/bic_proof_common.R")

A <- fixture(1:9, 1:10, models14[1:10])     # 9 x 10, NA where (G+j) %% 7 == 0
B <- fixture(2:10, 5:14, models14[5:14])    # 9 x 10
E <- fixture(1:2, 1:2, models14[1:2])       # 2 x 2 (k larger than the entries)
D <- fixture(1:3, 1:2, models14[1:2]); D[] <- NA  # all NA

cases <- list(
  list(id = "A-k3", x = A, k = 3),
  list(id = "A-k1", x = A, k = 1),
  list(id = "B-k5", x = B, k = 5),
  list(id = "E-k10", x = E, k = 10),
  list(id = "D-allNA-k3", x = D, k = 3),
  list(id = "scalar-k3", x = 5, k = 3)
)

run_all <- function() {
  lapply(cases, function(cs) suppressWarnings(pickBIC(cs$x, k = cs$k)))
}

res <- run_all()  # one untimed call, used for the records

rec <- character(0)
for (i in seq_along(cases)) {
  out <- paste0("case\t", cases[[i]]$id)
  x <- res[[i]]
  if (is.null(x)) {
    rec <- c(rec, out, "null\t1")
  } else {
    rec <- c(rec, out,
             line("values", fmt(x)),
             line("names", if (is.null(names(x))) "NULL" else names(x)))
  }
}

ms <- time_median_ms(run_all)
write_record("pickBIC", rec, ms)
cat("R pickBIC median ms:", ms, "\n")
