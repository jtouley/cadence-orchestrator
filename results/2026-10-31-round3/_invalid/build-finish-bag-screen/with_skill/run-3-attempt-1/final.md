The verifier's tests check out:
- **Suite:** 644 passed, 3 skipped. The browser test passes once Playwright is installed.
- **New tests:** all 6 fail on `main`, so they actually test the new behaviour.

One gap: no browser test clicks the Finish button, so its JavaScript handler has never run in a browser. I'll fold that into the fix round once the spec reviewer reports.