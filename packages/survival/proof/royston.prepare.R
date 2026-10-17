suppressPackageStartupMessages(library(survival))
stopifnot(identical(packageDescription("survival")$Version, "3.8-12"))

pbc2 <- na.omit(pbc)
cfit <- coxph(
  Surv(time, status == 2) ~ age + log(bili) + edema + albumin + stage + copper,
  data = pbc2,
  ties = "breslow"
)
proof <- "/home/ahmed/killr_projects/killr/packages/survival/proof"

write.csv(cfit$y, file.path(proof, "royston_y.csv"), row.names = FALSE)
write.csv(cfit$linear.predictors, file.path(proof, "royston_lp.csv"), row.names = FALSE)
write.csv(cfit$loglik, file.path(proof, "royston_loglik.csv"), row.names = FALSE)
write.csv(
  data.frame(nevent = cfit$nevent, n = cfit$n),
  file.path(proof, "royston_meta.csv"),
  row.names = FALSE
)
write.csv(cfit$coefficients, file.path(proof, "royston_coef.csv"), row.names = FALSE)
