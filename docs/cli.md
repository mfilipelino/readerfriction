# CLI quick reference

Normative contract: [`spec/cli.md`](../spec/cli.md).

```
readerfriction scan <path>          # metrics + summary
readerfriction trace <file>:<func>  # chosen trace path
readerfriction explain <file>:<func># wrapper classification detail
readerfriction report <path>        # markdown / json / text report
readerfriction diff <path> --base <other-path>
```

Global flags: `--format {text,json,markdown}`, `--out <file>`,
`--fail-on 'metric OP number'`, `--exclude <glob>`, `--config <pyproject.toml>`,
`--no-color`.

Exit codes: `0` success · `1` `--fail-on` triggered · `2` usage · `3` internal
error.
