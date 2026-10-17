.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(rstudioapi))
stopifnot(identical(as.character(packageVersion("rstudioapi")), "0.19.0"))

line <- function(name, expr) {
  text <- tryCatch(
    {
      value <- expr
      if (isTRUE(value)) {
        "TRUE"
      } else if (identical(value, FALSE)) {
        "FALSE"
      } else {
        paste0("OTHER ", paste(as.character(value), collapse = ","))
      }
    },
    error = function(e) paste0("ERR ", conditionMessage(e))
  )
  paste0(name, "=", text)
}

restore <- function(name, previous) {
  if (is.na(previous)) {
    Sys.unsetenv(name)
  } else {
    do.call(Sys.setenv, setNames(list(previous), name))
  }
}

one <- function() {
  wb <- Sys.getenv("RSTUDIO_WORKBENCH_JOB", unset = NA_character_)
  ipc <- Sys.getenv("RSTUDIOAPI_IPC_REQUESTS_FILE", unset = NA_character_)
  response <- Sys.getenv("RSTUDIOAPI_IPC_RESPONSE_FILE", unset = NA_character_)
  secret <- Sys.getenv("RSTUDIOAPI_IPC_SHARED_SECRET", unset = NA_character_)
  rstudio <- Sys.getenv("RSTUDIO", unset = NA_character_)
  on.exit({
    restore("RSTUDIO_WORKBENCH_JOB", wb)
    restore("RSTUDIOAPI_IPC_REQUESTS_FILE", ipc)
    restore("RSTUDIOAPI_IPC_RESPONSE_FILE", response)
    restore("RSTUDIOAPI_IPC_SHARED_SECRET", secret)
    restore("RSTUDIO", rstudio)
  }, add = TRUE)
  Sys.unsetenv("RSTUDIO_WORKBENCH_JOB")
  Sys.unsetenv("RSTUDIOAPI_IPC_REQUESTS_FILE")
  Sys.unsetenv("RSTUDIOAPI_IPC_RESPONSE_FILE")
  Sys.unsetenv("RSTUDIOAPI_IPC_SHARED_SECRET")
  Sys.unsetenv("RSTUDIO")

  parts <- c(
    line("default", isAvailable()),
    line("version", isAvailable(version_needed = "2024.04.2")),
    line("child", isAvailable(child_ok = TRUE)),
    line("both", isAvailable(version_needed = "0.99.0", child_ok = FALSE)),
    line("null", isAvailable(child_ok = NULL)),
    line("string", isAvailable(child_ok = "TRUE")),
    line("len2", isAvailable(child_ok = c(TRUE, FALSE))),
    line("zero", isAvailable(child_ok = 0)),
    line("one", isAvailable(child_ok = 1)),
    line("nan", isAvailable(child_ok = NaN)),
    line("empty", isAvailable(child_ok = logical(0))),
    line("zeroi", isAvailable(child_ok = 0i)),
    line("onei", isAvailable(child_ok = 1i))
  )
  Sys.setenv(RSTUDIO = "1")
  parts <- c(
    parts,
    line("rstudio-env", isAvailable()),
    line("rstudio-env-child", isAvailable(child_ok = TRUE))
  )
  Sys.unsetenv("RSTUDIO")
  Sys.setenv(RSTUDIO_WORKBENCH_JOB = "1")
  parts <- c(
    parts,
    line("wb-default", isAvailable()),
    line("wb-child", isAvailable(child_ok = TRUE)),
    line("wb-version", isAvailable(version_needed = "99.0", child_ok = TRUE)),
    line("wb-na", isAvailable(child_ok = NA)),
    line("wb-zeroi", isAvailable(child_ok = 0i)),
    line("wb-onei", isAvailable(child_ok = 1i))
  )
  Sys.unsetenv("RSTUDIO_WORKBENCH_JOB")
  Sys.setenv(RSTUDIOAPI_IPC_REQUESTS_FILE = "")
  parts <- c(
    parts,
    line("ipc-child", isAvailable(child_ok = TRUE)),
    line("ipc-false", isAvailable(child_ok = FALSE))
  )
  paste(parts, collapse = "\n")
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
