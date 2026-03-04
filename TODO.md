# TODO

## Locale-independent output constants

`Event.__str__()` and `format_event()` use `strftime("%b")` and `strftime("%a")`
which produce locale-dependent month/weekday abbreviations. For full robustness
on systems with non-English locales, these should use constant English
abbreviation tuples instead of relying on the C locale being active at output
time.
