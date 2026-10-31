I couldn't reproduce this on `main`, so I haven't changed anything.

On `main`, an 18 g in / 37 g out shot shows **1:2.06** on the saved screen, not 1:2.0. The ratio is shown with two decimals, and 37/18 = 2.0556 rounds correctly to 2.06. The offline saved view does the same. A worker saved that exact shot in a test and loaded the saved page, and I checked the template lines it cited.

The only "1:2.0" on that page is a fixed gridline label on the chart under the number (1:1.8, 1:2.0, 1:2.2, 1:2.4). That may be what you saw.

Which one is it?
1. It was the chart label, so nothing to fix.
2. You want the big ratio shown with one decimal (1:2.1). That's a design change: the mockup and a test both expect two decimals.
3. You saw 1:2.0 as the big number on a particular build or device. A screenshot would help.

Nothing was committed to the code, pushed, or opened as a PR. The status is recorded on the local `orchestration` branch in `workstreams/saved-ratio-rounding.md`.