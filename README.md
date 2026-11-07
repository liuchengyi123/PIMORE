# PIMORE (Harbor)

Harbor 独立站 monorepo：后端、H5、uni-app、客服桌面端。

## 包含

| 目录 | 说明 |
|------|------|
| `shop/` | FastAPI 店铺后端 |
| `harbor-web/` | Vue3 + Vite H5 |
| `harbor-app/` | uni-app + Capacitor |
| `harbor-cs-desktop/` | Electron 客服台 |
| `docs/` | 需求与运营文档 |
| `tests/` | pytest |
| `deploy/` | 部署片段 |

原生 App 在独立仓库：
- https://github.com/liuchengyi123/harbor-android
- https://github.com/liuchengyi123/harbor-ios

## 本地启动（摘要）

```bat
start-shop-8787.bat
cd harbor-web && npm run dev
```

店铺默认 `http://127.0.0.1:8787`，H5 `http://127.0.0.1:5174`。

商品图、sqlite、`.env` 不入库，需本机或服务器另行同步。
