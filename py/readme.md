# py 模块说明

## 当前结构

- `app.py`: 应用工厂入口。
- `bootstrap.py`: 服务容器装配。
- `core/`: 核心配置与日志。
- `api/main.py`: FastAPI 入口，基于 `app.create_app()` 构建应用。
- `start.py`: 本地启动脚本。
- `auth/`、`game/`、`mcp_server/`、`agent_chat/`、`skill_adapters/`、`workflow_adapter/`:
  真实实现目录。
- `tests/`: 可回归单测。

## 设计原则

- 使用应用工厂替代模块级初始化。
- 配置集中到 `core.settings`。
- 业务逻辑、路由、协议适配分层。
- Redis 不可用时自动回退到内存会话存储，避免导入时直接失败。

## 本地运行

在使用命令行时，需要先执行：

```powershell
conda activate ai
```

启动服务：

```powershell
python py/start.py
```

运行核心单测：

```powershell
python -m unittest py.tests.test_agent_chat py.tests.test_mcp_server py.tests.test_app_auth_game
```
