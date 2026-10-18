The door transport now distinguishes request failures from parse failures and
retains the returned or provider-cached response without retrying. Live probe
failures write a redacted-by-length evidence record with the full-body SHA-256
and a 4000-character JSON preview, then identify that file in the failed row
and run failure. Offline tests cover response retention, one-request budget
accounting, request-stage errors, and artifact hashing/truncation. Dry mode is
unchanged and remains network-free.
