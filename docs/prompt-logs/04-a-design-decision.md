# A design decision: how logout behaves

The B3 reviewer noticed that logout required a valid session. The agent brought me the decision
instead of just changing the API:

**Agent (excerpt):**
> The key fact is that **the frontend can't delete this cookie itself.** It's httpOnly, so page
> JavaScript can't touch it. [...]
> **Option A: keep it as is** — ❌ If the cookie goes stale [...] logout returns 401 and the dead
> cookie stays in the browser. [...] That's how the redirect loop happens.
> **Option B: logout always works** — ✅ No security cost. Clearing a cookie gives nobody access
> to anything. ❌ Another website could log an attorney out [...] an annoyance, not a breach.

**Me:**
> the frontend would need to know about this change right? afterwards explain to me how this
> works since my understanding of auth is naive.

The agent explained the whole flow: the bcrypt hash, what is inside the JWT and why the signature
makes it trustworthy, the cookie flags, and the limits of stateless logout.

**Me:**
> yes lets go with B

The change went into B3 (`a98004c`), DESIGN.md recorded why, and the frontend lane got a new rule:
on any 401, call logout, then go to `/login`.
