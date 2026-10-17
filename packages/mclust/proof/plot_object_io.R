# Dumps and reads the fitted objects the mclust plot proofs share.
#
# dump_mclust_object() writes one JSON file per fitted object. The R plot
# proofs read that file back with read_mclust_object(), and the Python proofs
# read the same file with plot_object_io.py, so both sides draw from the same
# numbers. Numeric nodes carry their dim (column-major values, NA as null).

.json_dim <- function(x) {
  d <- dim(x)
  if (is.null(d)) "null" else paste0("[", paste(d, collapse = ","), "]")
}
.json_str <- function(s) paste0('"', gsub('"', '\\\\"', s), '"')
.json_num <- function(v) {
  v <- as.numeric(v)
  s <- ifelse(is.na(v), "null", sprintf("%.17g", v))
  paste0("[", paste(s, collapse = ","), "]")
}
.node_num <- function(x) {
  if (is.null(x)) return("null")
  paste0('{"t":"n","dim":', .json_dim(x), ',"v":', .json_num(x), "}")
}
.node_chr <- function(x) {
  if (is.null(x)) return("null")
  vals <- paste(vapply(as.character(x), .json_str, ""), collapse = ",")
  paste0('{"t":"c","dim":', .json_dim(x), ',"v":[', vals, "]}")
}
.node_obj <- function(named) {
  named <- named[!vapply(named, is.null, TRUE)]
  paste0("{", paste0('"', names(named), '":', unlist(named), collapse = ","), "}")
}
.node_bic <- function(b) {
  .node_obj(list(
    values = .node_num(matrix(as.vector(b), nrow(b), ncol(b))),
    G = .node_num(attr(b, "G")),
    modelNames = .node_chr(attr(b, "modelNames")),
    rownames = .node_chr(dimnames(b)[[1]]),
    colnames = .node_chr(dimnames(b)[[2]]),
    returnCodes = .node_num(as.vector(attr(b, "returnCodes")))
  ))
}
.node_pars <- function(p) {
  vnodes <- lapply(p$variance, function(z) if (is.character(z)) .node_chr(z) else .node_num(z))
  .node_obj(list(pro = .node_num(p$pro), mean = .node_num(p$mean),
                 variance = .node_obj(vnodes)))
}

dump_mclust_object <- function(m, path) {
  f <- list(
    data = .node_num(m$data),
    colnames = .node_chr(colnames(m$data)),
    d = .node_num(m$d), G = .node_num(m$G), n = .node_num(m$n),
    modelName = .node_chr(m$modelName),
    classification = .node_num(m$classification),
    uncertainty = .node_num(m$uncertainty),
    z = .node_num(m$z),
    density = if (is.null(m$density)) NULL else .node_num(m$density),
    hypvol = if (is.null(m$hypvol)) NULL else .node_num(m$hypvol),
    BIC = .node_bic(m$BIC),
    parameters = .node_pars(m$parameters),
    class = .node_chr(class(m))
  )
  writeLines(.node_obj(f), path)
  invisible(path)
}

.dec_num <- function(n) {
  if (is.null(n)) return(NULL)
  v <- vapply(n$v, function(z) if (is.null(z)) NA_real_ else as.numeric(z), 0)
  if (is.null(n$dim)) v else array(v, dim = unlist(n$dim))
}
.dec_chr <- function(n) if (is.null(n)) NULL else unlist(n$v)

read_mclust_object <- function(path) {
  j <- jsonlite::fromJSON(path, simplifyVector = FALSE)
  variance <- list()
  for (nm in names(j$parameters$variance)) {
    node <- j$parameters$variance[[nm]]
    variance[[nm]] <- if (identical(node$t, "c")) .dec_chr(node) else .dec_num(node)
  }
  b <- j$BIC
  bic <- .dec_num(b$values)
  dimnames(bic) <- list(.dec_chr(b$rownames), .dec_chr(b$colnames))
  attr(bic, "G") <- .dec_num(b$G)
  attr(bic, "modelNames") <- .dec_chr(b$modelNames)
  attr(bic, "returnCodes") <- .dec_num(b$returnCodes)
  class(bic) <- "mclustBIC"
  data <- .dec_num(j$data)
  cn <- .dec_chr(j$colnames)
  if (!is.null(cn)) dimnames(data) <- list(NULL, cn)
  obj <- list(
    call = NULL,
    data = data,
    modelName = .dec_chr(j$modelName),
    n = .dec_num(j$n),
    d = .dec_num(j$d),
    G = .dec_num(j$G),
    BIC = bic,
    parameters = list(pro = .dec_num(j$parameters$pro),
                      mean = .dec_num(j$parameters$mean),
                      variance = variance),
    z = .dec_num(j$z),
    classification = .dec_num(j$classification),
    uncertainty = .dec_num(j$uncertainty)
  )
  if (!is.null(j$density)) obj$density <- .dec_num(j$density)
  if (!is.null(j$hypvol)) obj$hypvol <- .dec_num(j$hypvol)
  class(obj) <- .dec_chr(j$class)
  obj
}
