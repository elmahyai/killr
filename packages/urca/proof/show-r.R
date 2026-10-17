.libPaths(c(path.expand("~/R/library"), path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(urca))
suppressPackageStartupMessages(library(vars))
if (as.character(packageVersion("urca")) != "1.3.4") stop("expected urca 1.3-4")
options(warn = -1)
x <- c(-0.62645381074233242, -0.44281048652025018, -1.2784390989302974, 0.31684170320749422, 0.64634947502285467, -0.17411890909516053, 0.31331014333332474, 1.051634848462542, 1.6274162001160344, 1.3220278129596783, 2.8338089814105265, 3.2236522178219573, 2.6024116372801536, 0.3877117501026538, 1.5126426682457619, 1.4677090592305311, 1.451518796131585, 2.3953550068168843, 3.2165762019149726, 3.8104775231324814, 4.7294548947406998, 5.5115911954717669, 5.5861561788369576, 3.5968044829735848, 4.2166302308682955, 4.1605014913392946, 4.004705984633965, 2.5339536007346903, 2.0558035456260702, 2.4737451058257727, 3.8324246573548164, 3.7296369300118211, 4.1173085415711901, 4.0635035009882854, 2.6864439441596786, 2.2714493808599987, 1.8771594271496495, 1.8178460304384638, 2.9178714024223469, 3.6810471508798912)
json_str <- function(s) {
  s <- enc2utf8(paste(s, collapse = "\n"))
  cps <- utf8ToInt(s)
  parts <- vapply(cps, function(cp) {
    if (cp == 34) paste0("\\", '"')
    else if (cp == 92) paste0("\\", "\\")
    else if (cp == 10) paste0("\\", "n")
    else if (cp == 13) paste0("\\", "r")
    else if (cp == 9) paste0("\\", "t")
    else if (cp < 32 || cp == 127) sprintf("\\u%04x", cp)
    else intToUtf8(cp)
  }, "")
  paste0('"', paste(parts, collapse = ""), '"')
}
normalize <- function(text) {
  lines <- strsplit(text, "\n", fixed = TRUE)[[1]]
  lines <- trimws(lines, which = "right")
  lines <- gsub(" +", " ", lines, perl = TRUE)
  out <- character(0)
  prev_blank <- FALSE
  for (line in lines) {
    blank <- nchar(line) == 0
    if (blank && prev_blank) next
    out <- c(out, line)
    prev_blank <- blank
  }
  paste(out, collapse = "\n")
}
one <- function() {
  df <- ur.df(x, type = "drift", lags = 1)
  kp <- ur.kpss(x, type = "mu", lags = "short")
  jo <- ca.jo(Canada, type = "trace", ecdet = "const", K = 2, spec = "longrun")
  parts <- c(
    capture.output(show(df)),
    capture.output(show(kp)),
    capture.output(show(jo)),
    capture.output(show(summary(df)))
  )
  normalize(paste(parts, collapse = "\n"))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_str(value), median(elapsed) * 1000))
