@echo off
cd /d D:\1010
set SHOP_DB=D:\1010\data\shop-live.sqlite
set ADMIN_USER=admin
set ADMIN_PASSWORD=harbor-local
set HARBOR_H5_ORIGIN=http://127.0.0.1:5174
echo Starting shop on 8787 with %SHOP_DB%
"C:\Program Files\Python312\python.exe" -m uvicorn shop.app:app --host 127.0.0.1 --port 8787
