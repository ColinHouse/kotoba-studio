# docs

The documentation site. `docs/` is both the VitePress root and an ordinary
folder of markdown, so every page renders on GitHub and on the site from the
same file — there is no second copy to keep in sync.

```bash
make docs        # serve at http://localhost:5173
make docs-build  # build into docs/.vitepress/dist
```

## Why `overrides` exists in package.json

VitePress 1.6.4 is the current stable release and it pins Vite 5, which pulls a
version of esbuild carrying dev-server advisories. There is no upgrade path:
VitePress 2 is still alpha, so Dependabot cannot resolve a fix and its security
update fails instead of opening a pull request.

The advisories are all build-time only — `npm audit --omit=dev` reports nothing,
and none of this code reaches the published static site. The overrides are here
anyway because they cost nothing: forcing esbuild >= 0.25 and Vite >= 6.4.3
builds byte-for-byte the same site and takes `npm audit` to zero, which keeps
the security tab quiet enough that a real alert will stand out.

Drop the overrides when VitePress 2 ships stable.
