# fragmented-flow

`main` calls six sibling helpers across different files. The reader has to
chase all of them to understand the flow.

Expected: moderate `trace_depth` (each helper is shallow) but high
`flow_fragmentation`. Few wrappers.
