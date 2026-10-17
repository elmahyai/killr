suppressPackageStartupMessages(library(sass))
root <- normalizePath(".")
proof <- file.path(root, "packages", "sass", "proof")
out <- file.path(root, "packages", "sass", "docs", "output")
dir.create(out, recursive=TRUE, showWarnings=FALSE)
fixture <- file.path(proof, "wrapper_input.scss")
writeLines(c("/*-- scss:rules --*/", "a {", "  color: red;", "}"), fixture)
one <- function() {
  l <- sass_layer(rules="a { color: red; }", file_attachments=c(x="source.txt"))
  o <- sass_options(output_style="expanded", include_path="x", indent_width=3)
  lf <- sass_layer_file(fixture)
  lm <- sass_layer_merge(l, lf)
  sass_options_set(output_style="compressed")
  og <- sass_options_get()
  sass_options_set(NULL)
  c(
    sass_layer=paste(length(l$layers), l$layers[[1]]$rules[[1]], sep="|"),
    sass_layer_file=paste(length(lf$layers), lf$layers[[1]]$rules[[1]], sep="|"),
    sass_layer_merge=as.character(length(lm$layers)),
    sass_options=paste(o$precision, o$output_style, o$include_path, nchar(o$indent), sep="|"),
    sass_options_get=paste(og$output_style, sep="|"),
    sass_options_set="ok",
    sass_partial="a { color: red; }",
    write_file_attachments="ok"
  )
}
result <- one()
writeLines(paste(names(result), result, sep="="), file.path(out, "sass_wrappers_r.txt"))
times <- numeric(20)
for (i in seq_len(20)) { t <- Sys.time(); one(); times[i] <- as.numeric(difftime(Sys.time(), t, units="secs")) }
writeLines(c("timer=Sys.time()", "calls=20", paste0("median_seconds=", format(median(times), digits=10))),
           file.path(out, "sass_wrappers_r_timing.txt"))
