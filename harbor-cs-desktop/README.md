# Harbor CS Desktop

独立桌面客服台（Electron）。

## 先启动店铺

```bat
D:\1010\start-shop-8787.bat
```

必须带 `SHOP_DB=D:\1010\data\shop-live.sqlite`，否则会落到空内存库或只有种子商品的小库。

## 启动客服台

```bat
cd /d D:\1010\harbor-cs-desktop
npm start
```

或双击 `start.bat`。

## 登录账号

- 地址：`http://127.0.0.1:8787`
- 账号：`admin`
- 密码：`harbor-local`

## 打包

```bat
npm run dist
```
