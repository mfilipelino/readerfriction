# Traceability Matrix

| REQ    | Source (`start.md` §)         | Module(s)                                      | Test(s)                                                      |
|--------|-------------------------------|-------------------------------------------------|--------------------------------------------------------------|
| REQ-001| Recommended stack             | `pyproject.toml`                               | `test_req_001_installable`                                   |
| REQ-002| CLI surface                   | `cli.py`                                       | `test_req_002_console_script`                                |
| REQ-003| Recommended stack             | `pyproject.toml`                               | `test_req_003_python_version`                                |
| REQ-010| CLI surface                   | `cli.py`                                       | `test_req_010_five_commands`                                 |
| REQ-011| CLI surface                   | `cli.py`                                       | `test_req_011_help_all_commands`                             |
| REQ-012| CLI surface                   | `reports/json_report.py`                       | `test_req_012_json_validates`                                |
| REQ-013| CLI surface                   | `reports/markdown.py`                          | `test_req_013_markdown_deterministic`                        |
| REQ-014| CLI surface                   | `cli.py`                                       | `test_req_014_out_flag`                                      |
| REQ-020| Acceptance criteria           | `parser/discover.py`                           | `test_req_020_recursive_discovery`                           |
| REQ-021| —                             | `parser/discover.py`                           | `test_req_021_default_excludes`                              |
| REQ-022| CLI surface                   | `parser/discover.py`, `cli.py`                 | `test_req_022_exclude_flag`                                  |
| REQ-023| Acceptance criteria           | `parser/discover.py`                           | `test_req_023_lexicographic_order`                           |
| REQ-030| Suggested structure           | `parser/ast_parse.py`                          | `test_req_030_module_ir`                                     |
| REQ-031| —                             | `parser/ast_parse.py`, `cli.py`                | `test_req_031_syntax_error_recorded`                         |
| REQ-032| Suggested structure           | `parser/ast_parse.py`                          | `test_req_032_function_ir_fields`                            |
| REQ-040| Acceptance criteria           | `parser/entrypoints.py`                        | `test_req_040_entrypoint_detection`                          |
| REQ-041| —                             | `parser/entrypoints.py`                        | `test_req_041_entrypoint_fallback`                           |
| REQ-050| Suggested structure           | `graph/callgraph.py`                           | `test_req_050_digraph_built`                                 |
| REQ-051| —                             | `graph/callgraph.py`, `graph/resolve.py`       | `test_req_051_external_sentinel`                             |
| REQ-052| —                             | `graph/callgraph.py`                           | `test_req_052_cycles_preserved`                              |
| REQ-060| Core metrics                  | `metrics/trace_depth.py`                       | `test_req_060_trace_depth`                                   |
| REQ-061| Core metrics                  | `metrics/file_jumps.py`                        | `test_req_061_file_jumps`                                    |
| REQ-062| Core metrics                  | `metrics/wrapper_depth.py`                     | `test_req_062_wrapper_depth`                                 |
| REQ-063| Core metrics                  | `metrics/thin_wrappers.py`                     | `test_req_063_thin_wrapper_count`                            |
| REQ-064| Core metrics                  | `metrics/flow_fragmentation.py`                | `test_req_064_flow_fragmentation`                            |
| REQ-065| Core metrics                  | `metrics/context_width.py`                     | `test_req_065_context_width`                                 |
| REQ-066| Core metrics                  | `metrics/pass_through_ratio.py`                | `test_req_066_pass_through_ratio`                            |
| REQ-067| Core score                    | `metrics/score.py`                             | `test_req_067_aggregate_score`                               |
| REQ-070| Thin wrapper heuristic        | `classify/wrappers.py`                         | `test_req_070_wrapper_classifier`                            |
| REQ-071| Thin wrapper heuristic        | `classify/wrappers.py`                         | `test_req_071_wrapper_rules_recorded`                        |
| REQ-080| Core score                    | `config.py`                                    | `test_req_080_pyproject_loaded`                              |
| REQ-081| Core score                    | `config.py`, `cli.py`                          | `test_req_081_cli_overrides`                                 |
| REQ-082| Core score                    | `config.py`                                    | `test_req_082_weights_configurable`                          |
| REQ-090| CLI surface                   | `reports/json_report.py`                       | `test_req_090_scan_schema_valid`                             |
| REQ-091| CLI surface                   | `reports/json_report.py`                       | `test_req_091_trace_schema_valid`                            |
| REQ-092| CLI surface                   | `reports/json_report.py`                       | `test_req_092_explain_schema_valid`                          |
| REQ-093| CLI surface                   | `reports/json_report.py`                       | `test_req_093_report_schema_valid`                           |
| REQ-094| CLI surface                   | `models.py`                                    | `test_req_094_schema_parity`                                 |
| REQ-100| CLI surface                   | `cli.py`                                       | `test_req_100_exit_zero`                                     |
| REQ-101| CLI surface                   | `cli.py`                                       | `test_req_101_fail_on_exit_one`                              |
| REQ-102| CLI surface                   | `cli.py`                                       | `test_req_102_usage_exit_two`                                |
| REQ-103| CLI surface                   | `cli.py`                                       | `test_req_103_error_exit_three`                              |
| REQ-900| Do not try to solve           | (absence)                                      | `test_req_900_no_dynamic_dispatch`                           |
| REQ-901| Do not try to solve           | (absence)                                      | `test_req_901_no_runtime_tracing`                            |
| REQ-902| Do not try to solve           | (absence)                                      | `test_req_902_python_only`                                   |
| REQ-903| Do not try to solve           | `parser/entrypoints.py`                        | `test_req_903_no_framework_magic`                            |

Every test id in this table is asserted to exist by `tests/test_traceability.py`.
