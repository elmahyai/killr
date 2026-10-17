.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(openssl))
KEY_HEX <- "3082013b020100024100b4c90a4d2a92b08723b9c283c59ab0d337b773bcf76500ece62f856f86d3ad1e67e6da90c54008b7128d2f3330925229539cf8f220b8fa706864b6549e5058130203010001024047aed778d582a8a04d1820faa2e5bd6b62d249000a9070177f0624c09e135cb6e119b6252cec4196262f3d3322177142e3b5c549345a47ca33e63eae5ef7cd41022100d9d90e9e97920c28f6fb0ee34aa16cc7467a28fab4a875b24adf57a524d81a51022100d472541091cbb69607d0972d17130c2cbecf758f55ce285edfddbb528f1a0f23022026a89c2d8c9c40482cbc14c245062c75988e29238457b8bb310a3d55731a5e61022100cf787f8456fdbce833e58f5da7852084aa2b6c4178a8866070fbd7ae3eb652450221008dc41791d6391f8c184e04bfc033862e4a3f0f513dfa2f998c0e7986b64fb929"
n <- nchar(KEY_HEX)
key <- read_key(as.raw(strtoi(substring(KEY_HEX, seq(1, n, 2), seq(2, n, 2)), 16L)))
one <- function() {
  hash <- as.raw(1:32)
  paste(as.integer(rsa_sign(hash, key)), collapse = ",")
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
shown <- enc2utf8(paste(as.character(value), collapse = "|"))
shown <- gsub("\n", " / ", shown, fixed = TRUE)
cat("VALUE ", shown, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
