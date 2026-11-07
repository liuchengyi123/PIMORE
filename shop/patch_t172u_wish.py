from pathlib import Path
path = Path(r"D:\1010\shop\app.py")
src = path.read_text(encoding="utf-8")
old = '''    @app.get("/account/wishlist", response_class=HTMLResponse)
    def wishlist(request: Request):
        ctx = view(request)
        wanted = set(read_skus(request.cookies.get("wishlist"), 36))
        items = [present(row, ctx) for row in catalog_rows() if row["sku"] in wanted]
        suggestions = []
        if not items:
            suggestions = [present(row, ctx) for row in catalog_rows() if row["stock"] > 0][:4]
        return templates.TemplateResponse(
            request, "account.html", {**ctx, "panel": "wishlist", "items": items, "suggestions": suggestions}
        )'''
new = '''    @app.get("/account/wishlist", response_class=HTMLResponse)
    def wishlist(request: Request):
        # Indexed/batched lookups only — never scan+present the full catalog.
        ctx = view(request)
        wanted = read_skus(request.cookies.get("wishlist"), 36)
        index = catalog_index()
        items = []
        for sku in wanted:
            row = index.get(sku)
            if row is not None:
                items.append(present(row, ctx))
        suggestions = []
        if not items:
            hint_rows = conn.execute(
                "select * from products where published = 1 and stock > 0 order by rowid limit 4"
            ).fetchall()
            suggestions = [present(dict(row), ctx) for row in hint_rows]
        return templates.TemplateResponse(
            request, "account.html", {**ctx, "panel": "wishlist", "items": items, "suggestions": suggestions}
        )'''
if old not in src:
    raise SystemExit('wishlist block not found exactly')
path.write_text(src.replace(old, new, 1), encoding='utf-8')
print('wishlist patched OK')
i = path.read_text(encoding='utf-8').find('@app.get("/account/wishlist"')
print(path.read_text(encoding='utf-8')[i:i+950])
