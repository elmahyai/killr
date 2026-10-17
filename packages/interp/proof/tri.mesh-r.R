# Proof: R interp::tri.mesh on fixed point sets. Run from packages/interp.
source("proof/interp_proof_common.R")

cases <- point_cases()

run_all <- function() {
  lapply(cases, function(cs) tri.mesh(cs$x, cs$y, duplicate = cs$dup))
}

res <- run_all() # one untimed call, used for the records

rec <- list()
for (i in seq_along(cases)) {
  cs <- cases[[i]]
  t <- res[[i]]
  ct <- canon_tri(t$trlist, t$cclist)
  id <- cs$id
  rec[[paste0(id, "/n")]] <- t$n
  rec[[paste0(id, "/x")]] <- t$x
  rec[[paste0(id, "/y")]] <- t$y
  rec[[paste0(id, "/nt")]] <- t$nt
  rec[[paste0(id, "/nchull")]] <- t$nchull
  rec[[paste0(id, "/chull")]] <- t$chull
  rec[[paste0(id, "/narcs")]] <- t$narcs
  rec[[paste0(id, "/arcs")]] <- rowmajor(t$arcs)
  rec[[paste0(id, "/tri")]] <- rowmajor(ct$tri)
  rec[[paste0(id, "/cc")]] <- rowmajor(ct$cc)
  rec[[paste0(id, "/trlist_raw")]] <- rowmajor(t$trlist)
}

ms <- median_ms(run_all, reps = 20)
write_record("docs/output/tri.mesh-r.txt", rec, ms)
cat("R tri.mesh cases:", length(cases), " median ms:", ms, "\n")
