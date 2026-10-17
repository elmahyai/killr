.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(farver))
stopifnot(as.character(packageVersion("farver")) == "2.1.2")
flat <- function(x) {
  if (is.null(x)) return("")
  if (is.character(x)) return(paste(ifelse(is.na(x), "NA", x), collapse = ","))
  if (is.integer(x) && !is.matrix(x)) return(paste(ifelse(is.na(x), "NA", as.character(x)), collapse = ","))
  paste(vapply(as.numeric(as.vector(x)), function(v) if (is.na(v)) "NA" else sprintf("%.16g", v), ""), collapse = ",")
}
r <- decode_colour(c("#FF0000","#FF9900","#CCFF00","#33FF00","#00FF66","#00FFFF","#0066FF","#3300FF","#CC00FF","#FF0099"))
h <- decode_colour(c("#FF0000","#FF1700","#FF2E00","#FF4600","#FF5D00","#FF7400","#FF8B00","#FFA200","#FFB900","#FFD100","#FFE800","#FFFF00","#FFFF2A","#FFFF80","#FFFFD5"))
h_luv <- convert_colour(h, "rgb", "luv")
one <- function() {
  paste(flat(compare_colour(r, h, "rgb", method = "cie2000")), flat(compare_colour(r, from_space = "rgb", method = "cmc")), flat(compare_colour(r, h_luv, "rgb", "luv")), sep = "|")
}
invisible(one())
elapsed <- numeric(20)
value <- NULL
for (i in seq_len(20)) {
  t0 <- Sys.time()
  value <- one()
  elapsed[[i]] <- as.numeric(Sys.time()) - as.numeric(t0)
}
cat(sprintf('{"value":"%s","median_ms":%.17g}\n', value, median(elapsed) * 1000))
