.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(urca))
if (as.character(packageVersion("urca")) != "1.3.4") stop("expected urca 1.3-4")
options(warn = -1)
x <- c(-0.62645381074233242, -0.44281048652025018, -1.2784390989302974, 0.31684170320749422, 0.64634947502285467, -0.17411890909516053, 0.31331014333332474, 1.051634848462542, 1.6274162001160344, 1.3220278129596783, 2.8338089814105265, 3.2236522178219573, 2.6024116372801536, 0.3877117501026538, 1.5126426682457619, 1.4677090592305311, 1.451518796131585, 2.3953550068168843, 3.2165762019149726, 3.8104775231324814, 4.7294548947406998, 5.5115911954717669, 5.5861561788369576, 3.5968044829735848, 4.2166302308682955, 4.1605014913392946, 4.004705984633965, 2.5339536007346903, 2.0558035456260702, 2.4737451058257727, 3.8324246573548164, 3.7296369300118211, 4.1173085415711901, 4.0635035009882854, 2.6864439441596786, 2.2714493808599987, 1.8771594271496495, 1.8178460304384638, 2.9178714024223469, 3.6810471508798912)
one <- function() {
  tau1 <- ur.sp(x, type = "tau", pol.deg = 1, signif = 0.01)
  rho2 <- ur.sp(x, type = "rho", pol.deg = 2, signif = 0.05)
  tau4 <- ur.sp(x, type = "tau", pol.deg = 4, signif = 0.1)
  c(
    as.numeric(tau1@teststat), as.numeric(tau1@cval), as.numeric(tau1@polynomial),
    as.numeric(rho2@teststat), as.numeric(rho2@cval), as.numeric(rho2@polynomial),
    as.numeric(tau4@teststat), as.numeric(tau4@cval), as.numeric(tau4@polynomial),
    as.numeric(tau1@res)
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(jsonlite::toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = FALSE, digits = 17, na = "null"))
