# Proof: R mclust::bic on fixed scalar inputs. Run from packages/mclust.
source("proof/bic_proof_common.R")

cases <- list(
  list(id = "VVV-G3-d4",       m = "VVV", ll = -1234.5, n = 150, d = 4, G = 3, noise = FALSE, eq = FALSE),
  list(id = "X-G2-d1-noise",   m = "X",   ll = -500.25, n = 100, d = 1, G = 2, noise = TRUE,  eq = FALSE),
  list(id = "EEE-G0-noise",    m = "EEE", ll = -800.125, n = 150, d = 4, G = 0, noise = TRUE,  eq = FALSE),
  list(id = "EII-G5-eqPro",    m = "EII", ll = -700,    n = 150, d = 4, G = 5, noise = FALSE, eq = TRUE),
  list(id = "XII-G4-d3",       m = "XII", ll = -650.5,  n = 120, d = 3, G = 4, noise = FALSE, eq = FALSE),
  list(id = "XXX-G4-noiseEq",  m = "XXX", ll = -640.75, n = 120, d = 3, G = 4, noise = TRUE,  eq = TRUE),
  list(id = "VEV-G2-d6",       m = "VEV", ll = -900.25, n = 200, d = 6, G = 2, noise = FALSE, eq = FALSE),
  list(id = "EVV-G1-noise",    m = "EVV", ll = -901,    n = 80,  d = 2, G = 1, noise = TRUE,  eq = FALSE),
  list(id = "E-G3-d1",         m = "E",   ll = -100.5,  n = 50,  d = 1, G = 3, noise = FALSE, eq = FALSE)
)

run_all <- function() {
  vapply(cases, function(cs)
    bic(cs$m, cs$ll, cs$n, cs$d, cs$G, noise = cs$noise, equalPro = cs$eq),
    numeric(1))
}

res <- run_all()  # one untimed call, used for the records

rec <- character(0)
for (i in seq_along(cases)) {
  rec <- c(rec, paste0("case\t", cases[[i]]$id), line("value", fmt(res[i])))
}

ms <- time_median_ms(run_all)
write_record("bic", rec, ms)
cat("R bic median ms:", ms, "\n")
