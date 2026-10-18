cat(jsonlite::toJSON(list(value=NULL,
                          waiting="dplyr, tidyr, tidyselect, purrr, rlang; htmlTable installation also lacks checkmate and htmlwidgets"),
                     auto_unbox=TRUE), "\n")
