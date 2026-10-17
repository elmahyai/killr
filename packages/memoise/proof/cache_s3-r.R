
.libPaths(c(path.expand("~/R/library"), .libPaths()))
options(cloudyr.aws.default_region = "", cloudyr.aws.allow_empty_region = TRUE)
Sys.setenv(
  AWS_ACCESS_KEY_ID = "testing",
  AWS_SECRET_ACCESS_KEY = "testing",
  AWS_DEFAULT_REGION = "",
  PYTHONPATH = "/home/ahmed/killr_projects/killr/packages/memoise"
)
ready <- tempfile("s3ready")
system2(
  "/home/ahmed/killr_projects/killr/.venv/bin/python",
  c("-m", "memoise._s3mock", ready),
  wait = FALSE, stdout = FALSE, stderr = FALSE
)
for (i in 1:100) {
  if (file.exists(ready) && file.info(ready)$size > 0) break
  Sys.sleep(0.05)
}
info <- jsonlite::fromJSON(paste(readLines(ready, warn = FALSE), collapse = ""))
Sys.setenv(
  AWS_S3_ENDPOINT = paste0("127.0.0.1:", info$port),
  SSL_CERT_FILE = info$cert,
  CURL_CA_BUNDLE = info$cert
)
httr::set_config(httr::config(cainfo = info$cert))
suppressPackageStartupMessages(library(memoise))
json_num <- function(x) {
  parts <- sprintf("%.17g", as.numeric(x))
  if (length(parts) == 1) return(parts[[1]])
  paste0("[", paste(parts, collapse = ","), "]")
}
one <- function() {
  name <- paste0("bkt", sprintf("%08d", sample.int(1e8, 1)))
  s3 <- cache_s3(name)
  s3$set("abc", 4)
  got <- s3$get("abc")
  has <- s3$has_key("abc")
  nkeys <- length(s3$keys())
  s3$drop_key("abc")
  has2 <- s3$has_key("abc")
  c(got, as.integer(has), nkeys, as.integer(has2))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
