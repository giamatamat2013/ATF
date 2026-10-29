"""Builds the static site (the demo gallery, the docs and the logo) into site/.

Any static host takes the result: GitHub Pages (.github/workflows/pages.yml), Netlify (netlify.toml),
Vercel (vercel.json), Cloudflare Pages, S3 or plain nginx. Run it from the repo root:

    python tools/build_site.py [--out site] [--domain atf.example.com]

--domain writes a CNAME file, which GitHub Pages needs for a custom domain.
"""
import argparse
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="site")
    p.add_argument("--domain", default="")
    a = p.parse_args()
    out = ROOT / a.out
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copy(ROOT / "demos.html", out / "index.html")
    shutil.copytree(ROOT / "docs", out / "docs")
    shutil.copytree(ROOT / "assets", out / "assets")
    shutil.copy(ROOT / "README.md", out / "README.md")
    (out / ".nojekyll").write_text("")  # GitHub Pages: serve the files as they are
    if a.domain:
        (out / "CNAME").write_text(a.domain.strip() + "\n")
    print(f"site built in {out} ({sum(1 for f in out.rglob('*') if f.is_file())} files)")


if __name__ == "__main__":
    main()
