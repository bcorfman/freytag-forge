F27: the examples-file checker API and failure-record shape are unspecified; assumed examples are YAML under `examples/<scene>.yaml` with `accept` and `reject` line lists.
F28: the contract does not require a bridge in F01; assumed one minimal bridge event may be added so every section 8.1 kind has an address.
F29: the order and duplicate policy of compiled required dependencies are unspecified; assumed membership is the fixed contract and asserted as a set.
F30: the compiled representation of a realization without a claim is unspecified; assumed it is represented by no knowledge definition whose source names that realization.
F31: the compiler-version and source-digest public API is unspecified; assumed canonical JSON uses `model_dump(mode="json", by_alias=True)` and the fixture helper hashes schema, compiler version, and relative source-file bytes.
