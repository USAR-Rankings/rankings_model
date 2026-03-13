#Preload

# Scripts/Preload.R

suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(stringr)
  library(stringi)
  library(readr)
  library(jsonlite)
})

normalize_key <- function(x, ascii = TRUE) {
  x <- stringi::stri_enc_toutf8(x, is_unknown_8bit = TRUE)
  x <- stringi::stri_replace_all_regex(
    x, "[\\u2018\\u2019\\u02BC\\u0060\\u00B4]", "'"
  )
  x <- stringi::stri_replace_all_regex(x, "\\s+", " ")
  x <- stringr::str_trim(x)
  if (ascii) x <- stringi::stri_trans_general(x, "Latin-ASCII")
  toupper(x)
}

timeouts <- function(remDr, milliseconds) {
  qpath <- sprintf("%s/session/%s/timeouts", remDr$serverURL,
                   remDr$sessionInfo[["id"]])
  remDr$queryRD(
    qpath,
    method = "POST",
    qdata = jsonlite::toJSON(
      list(type = "implicit", ms = milliseconds),
      auto_unbox = TRUE
    )
  )
}