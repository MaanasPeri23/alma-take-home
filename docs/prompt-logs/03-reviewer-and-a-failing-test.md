# The reviewer, and a test that caught the reviewer

B2 added the public submission endpoint. The read-only reviewer subagent reported:

> **should-fix: `NAME_PATTERN`.** `[^\r\n]` still lets through NUL and other control characters.
> Postgres refuses NUL in text columns. [...] So `first_name="Ada\x00"` uploads the file, the
> commit fails, the file is deleted, and the prospect gets a 500 instead of a 422 on
> `first_name`.
> **Fix:** use `r"^[^\x00-\x1f\x7f]*\S[^\x00-\x1f\x7f]*$"`

Before applying the fix, the agent added a `nul-in-name` test case. After applying it:

```
FAILED ... sqlalchemy.exc.DataError: PostgreSQL text fields cannot contain NUL (0x00) bytes
1 failed, 46 passed
```

**Agent (excerpt):**
> The reviewer's suggested pattern has a hole. In `…\S…`, the middle `\S` means "any non-space
> character", and NUL counts as a non-space character. So `\S` itself matched the NUL.

It then checked the corrected pattern, `[^\s\x00-\x1f\x7f]`, against a table of inputs:

```
'Ada'              ok
'José'             ok
'Ada\x00'          rejected
'Ada\r\nBcc: x'    rejected
'   '              rejected
```

Commit `a13fbe9`. The same review also turned on `hide_parameters=True`, because a failed insert
would have logged the prospect's name and email.
