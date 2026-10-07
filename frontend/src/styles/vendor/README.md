# shadcn Tailwind stylesheet

`shadcn-tailwind.css` is an unmodified copy of `dist/tailwind.css` from
shadcn 4.16.2 (MIT). Its license is in `shadcn-LICENSE.md`.
Only this stylesheet was used by the application; no scripts or source imports
required the CLI package. Keeping the CSS locally avoids installing the CLI's
unpatched braces/fast-glob dependency graph. Existing Radix components remain.

Upstream: https://github.com/shadcn-ui/ui
Advisory: https://github.com/advisories/GHSA-vfj7-8cjw-p6xm

Updates must preserve the upstream license and review generated CSS equivalence.
