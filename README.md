# CloudEdge 云加速 · 客户自助门户（ISPweb）

面向终端客户的 VPS / 边缘加速 **选购 + 自助管理** 前端门户，数据对接 `ISPmanager` 中台后端的 `portal` 接口。

## 技术栈

- Vue 3 + Vite 5
- Element Plus + Icons
- Pinia（鉴权状态）/ Vue Router 4
- Axios（统一封装 + 401 自动刷新 Token）

## 功能

1. **官网与产品**：专业落地页、产品列表（区域/国家/城市/网络类型/IP属性/ASN 多维筛选）、产品详情与在线下单。
2. **账户**：注册（创建客户档案）、登录、修改密码、资料维护。
3. **自助控制台**：总览看板、我的服务（在线提交变更/定制申请）、我的订单、账单中心（逐项明细）、资源管理（VPS / 边缘加速）。

## 后端依赖

需 `ISPmanager` 后端已启用 `portal` 应用，提供 `/api/portal/*` 接口；登录/改密复用 `/api/auth/*`。

## 本地开发

```bash
npm install
npm run dev      # http://localhost:5180 ，/api 代理至 127.0.0.1:8000
```

## 生产构建

```bash
npm run build    # 产物输出至 dist/
```

> 生产部署时，将 `dist/` 交由 Nginx 托管，并把 `/api` 反向代理到 ISPmanager 后端即可。
