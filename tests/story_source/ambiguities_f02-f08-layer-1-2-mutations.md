F02: today-running loading behavior for a duplicate-key source is unspecified; assumed `load_tree` rejects the raw mutation with `yaml.YAMLError`.
F03: the diagnostic address and field formatting for an unknown reveal key are unspecified; assumed the diagnostic identifies the source file, address, and field without requiring a fixed spelling.
F04: the diagnostic address and field formatting for a fact with two owners are unspecified; assumed the diagnostic identifies the source file, address, and field without requiring a fixed spelling.
F05: the exact fact-declaration diagnostic wording is unspecified; assumed its message contains the declaration block name and the target scene file required by the contract.
F06: the diagnostic address and field formatting for an unauthorized claim subset are unspecified; assumed the diagnostic identifies the source file, address, and field without requiring a fixed spelling.
F07: the order and address formatting of the two override diagnostics are unspecified; assumed the test checks two `L2.override_add_only` diagnostics and their diagnostic metadata, independent of order.
F08: the order and address formatting of the four dangling-reference diagnostics are unspecified; assumed the test checks four `L2.dangling_ref` diagnostics and their diagnostic metadata, independent of order.
