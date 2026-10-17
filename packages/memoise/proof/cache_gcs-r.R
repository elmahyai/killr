
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(memoise))
root <- tempfile("gcsroot")
dir.create(root)
upload <- function(file, bucket = NULL, name = "object", ...) {
  dest <- file.path(root, bucket)
  dir.create(dest, showWarnings = FALSE, recursive = TRUE)
  file.copy(file, file.path(dest, name), overwrite = TRUE)
  invisible(TRUE)
}
download <- function(object_name, bucket = NULL, saveToDisk = NULL, overwrite = TRUE, ...) {
  file.copy(file.path(root, bucket, object_name), saveToDisk, overwrite = TRUE)
  TRUE
}
listing <- function(bucket = NULL, prefix = NULL, ...) {
  dest <- file.path(root, bucket)
  files <- if (dir.exists(dest)) list.files(dest) else character(0)
  if (!is.null(prefix)) files <- files[startsWith(files, prefix)]
  if (!length(files)) return(data.frame())
  data.frame(name = files, stringsAsFactors = FALSE)
}
remove_one <- function(object_name, bucket = NULL, ...) {
  unlink(file.path(root, bucket, object_name))
  TRUE
}
assignInNamespace("gcs_upload", upload, "googleCloudStorageR")
assignInNamespace("gcs_get_object", download, "googleCloudStorageR")
assignInNamespace("gcs_list_objects", listing, "googleCloudStorageR")
assignInNamespace("gcs_delete_object", remove_one, "googleCloudStorageR")
json_num <- function(x) {
  parts <- sprintf("%.17g", as.numeric(x))
  if (length(parts) == 1) return(parts[[1]])
  paste0("[", paste(parts, collapse = ","), "]")
}
one <- function() {
  name <- paste0("bkt", sprintf("%08d", sample.int(1e8, 1)))
  gcs <- cache_gcs(name)
  gcs$set("abc", 4)
  got <- gcs$get("abc")
  has <- gcs$has_key("abc")
  nkeys <- length(gcs$keys())
  gcs$drop_key("abc")
  has2 <- gcs$has_key("abc")
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
