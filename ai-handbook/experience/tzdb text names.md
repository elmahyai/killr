The text time zone files for tzdb 0.5.0 live inside `rcran/contrib/tzdb_0.5.0.tar.gz` at `tzdb/inst/tzdata`. They are not a separate data library.

`tzdb_names` reads Zone and Link records from africa, antarctica, asia, australasia, backward, etcetera, europe, pacificnew, northamerica, southamerica, systemv, and leapseconds, then sorts the names as raw bytes. `factory` and `backzone` are not read. In the 2025a database, `pacificnew` and `systemv` are absent, and the sorted list has 596 names. `tzdb_version` is the first token of the `version` file, which is `2025a`.
