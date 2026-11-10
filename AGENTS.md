# 项目说明

这个仓库是 UCloud Sandbox 的 Python SDK。UCloud Sandbox 服务的 API 与 E2B 完全兼容，所以这个项目本质上是把 E2B 相关 Python SDK 的上游代码同步到本仓库中，再在同步后的代码基础上修改环境变量名称、错误描述、文案和品牌信息，使其面向 UCloud Sandbox。

需要特别注意：本仓库不只是同步 E2B 主 Python SDK，还会把 code interpreter 和 desktop 两个 Python SDK 一起合并进来。这三个 SDK 现在都位于 E2B monorepo 内（早期 code interpreter 和 desktop 有各自的独立仓库，上游已经把它们迁进主仓库并删除了原仓库中的 Python 源码）。

因此，后续修改时要把 `ucloud_sandbox/` 视为合并后的 SDK 包，而不是单一上游目录的简单镜像。

# 目录结构

- `ucloud_sandbox/`
  - 本项目主要 SDK 代码目录。
  - 这是发布给用户使用的 Python 包主体。
  - 代码来源于 E2B monorepo 中的三个 Python SDK，同步后会继续进行 UCloud 相关改造。

- `upstream/`
  - 上游源码目录。
  - 这里的内容通过 git submodules 管理，通常不要直接在这里做业务修改。
  - 如果需要更新上游，应更新 submodule 后再运行同步脚本。

目前只有一个 submodule：

- `upstream/e2b`
  - 上游仓库：`https://github.com/e2b-dev/E2B.git`

上游包路径与同步目标的关系如下：

| 上游 Python SDK 位置 | 同步到 |
| --- | --- |
| `upstream/e2b/packages/python-sdk/e2b` | `ucloud_sandbox/` |
| `upstream/e2b/packages/code-interpreter-python/e2b_code_interpreter` | `ucloud_sandbox/code_interpreter/` |
| `upstream/e2b/packages/desktop-python/e2b_desktop` | `ucloud_sandbox/desktop/` |

后两者同步后保留本项目原有目录命名 `code_interpreter` 和 `desktop`。

# 同步脚本

- `scripts/sync_upstreams.sh`
  - 上游代码同步入口。
  - 会检查 `upstream/e2b` submodule 是否已经初始化；如果没有，会执行 `git submodule update --init --recursive`。
  - 会将三个上游 Python SDK 分别复制到 `ucloud_sandbox/`、`ucloud_sandbox/code_interpreter/` 和 `ucloud_sandbox/desktop/`。
  - 这个脚本只同步上游代码，不会自动同步依赖，也不会自动执行 UCloud 定制 hack。
  - 该脚本会覆盖 `ucloud_sandbox/`、`ucloud_sandbox/code_interpreter/` 和 `ucloud_sandbox/desktop/` 中的内容。运行前要确认当前工作区里的 UCloud 改造是否已经保存或确认可以被覆盖。

- `scripts/sync_dependencies.py`
  - 依赖同步脚本。
  - 会读取三个上游 Python SDK 的 `pyproject.toml`，合并依赖到根目录的 `pyproject.toml`。
  - 上游已经迁移到 uv / PEP 621，所以脚本从 `[project].dependencies`（PEP 508 字符串列表）和 `[dependency-groups]` 读取，而不是 `[tool.poetry.*]`。本仓库仍然使用 Poetry，脚本负责把结果写成 Poetry 格式。
  - 只更新根 `pyproject.toml` 中的 `[tool.poetry.dependencies]` 和 `[tool.poetry.group.dev.dependencies]` 两个 section。
  - 会保留 UCloud 项目的包名、描述、作者、仓库地址、packages 等元信息。
  - 会跳过上游的 `e2b` 运行时依赖，因为 E2B 主 SDK 源码已经被同步进 `ucloud_sandbox/`，不应再依赖官方发布的 `e2b` 包。
  - 会跳过上游的 `codegen` 依赖组，那是 E2B 自己的代码生成工具链，本项目用不到。
  - 对已知版本冲突使用脚本中的显式覆盖规则；遇到未知依赖冲突、无法解析的 requirement、或带 extras / environment marker 的 requirement 时会报错，避免静默选择错误版本或丢失信息。

推荐手动同步顺序如下：

```bash
scripts/sync_upstreams.sh
python3 scripts/sync_dependencies.py
python3 scripts/hack.py
```

# UCloud 定制 Hack

`scripts/hack.py` 用于在上游代码同步完成后，重新应用本项目的 UCloud Sandbox 定制。上游同步会把 `ucloud_sandbox/` 恢复成 E2B 原始代码，因此每次运行 `scripts/sync_upstreams.sh` 之后，都需要手动运行：

```bash
python3 scripts/hack.py
```

`scripts/hack.py` 主要做这些事情：

- 将 `ucloud_sandbox/` 内部的主 SDK import 从 `e2b` 改为 `ucloud_sandbox`。
- 将 code interpreter 内部的 `e2b_code_interpreter` import 改为 `ucloud_sandbox.code_interpreter`，desktop 内部的 `e2b_desktop` import 改为 `ucloud_sandbox.desktop`。
- 将上游公开客户端类 `E2B` 改名为 `UCloudSandbox`（`E2BClientParams` 对应改为 `UCloudSandboxClientParams`）。这一步必须在品牌文案替换之前执行，否则通用的 `\bE2B\b` → `UCloud Sandbox` 规则会把类名变成非法标识符 `class UCloud Sandbox:`。三个包各有一份 `client.py`，都会被处理。
- 将 docstring 和用户可见文档中的 `E2B` 改成 `UCloud Sandbox`。
- 将文档链接改成 `https://astraflow.ucloud.cn/docs/agent-sandbox/product/01-prerequisites`。
- 将环境变量从 `E2B_*` 改成 `UCLOUD_SANDBOX_*`。
- 将默认 domain 改成 `cn-wlcb.sandbox.ucloudai.com`。
- 额外支持 `UCLOUD_SANDBOX_REGION`，当该环境变量非空时，SDK 推导出的 domain 固定为 `{region}.sandbox.ucloudai.com`，并优先于 `UCLOUD_SANDBOX_DOMAIN`；显式传入的 `domain=` 参数仍然拥有最高优先级。
- 创建或恢复 `ucloud_sandbox/domain_config.py`，把 UCloud 专属的 domain 与 base image 推导逻辑集中在这个非上游 helper 中，避免把新增业务逻辑散落在从 E2B 同步来的文件里。该文件由 `scripts/hack.py` 中的 `DOMAIN_CONFIG_SOURCE` 常量整份生成，**任何对它的修改都必须改在那个常量里**，否则下次同步就会被覆盖回去。
- 从包根 `ucloud_sandbox/__init__.py` 导出 `get_ucloud_sandbox_domain`、`get_ucloud_sandbox_region`、`get_default_base_image`、`is_region_cn` 四个 helper。
- 额外支持 `UCLOUD_SANDBOX_INSECURE_HTTP` 和 `insecure_http=` 参数；为 `true` 时管理 API、sandbox、Code Interpreter、Desktop 和 Volume 的默认 URL 使用 HTTP，默认仍使用 HTTPS。
- 将 sandbox URL 固定为 `{protocol}://{port}-{sandbox_id}.{domain}` 的形式，不再走 `https://sandbox.<domain>`。
- 将 `metadata.version("e2b")` 改成 `metadata.version("ucloud_sandbox")`。
- 将 `publisher` 改成 `ucloud`。
- 将 User-Agent 改成 `ucloud-agentbox-sdk/{package_version}`。
- 将默认 base image 按 region 解析：`ucloud_sandbox/template/main.py` 的 `_default_base_image` 改为调用 `get_default_base_image()`，CN region（`cn`、`gray` 前缀）使用 `uhub.service.ucloud.cn/agent-sandbox-public/base_cn:latest`，其余使用 `uhub.service.ucloud.cn/agent-sandbox-public/base:latest`。上游代码里残留的 `e2bdev/base` 文案也一并替换成后者。
- 默认创建沙箱时使用带 `system/` 前缀的内置 template：未显式传 `template` 时，`base`、`mcp-gateway`、`code-interpreter-v1`、`desktop` 分别变为 `system/base`、`system/mcp-gateway`、`system/code-interpreter-v1`、`system/desktop`。用户显式传入不带前缀的名字不受影响；`template/main.py` 中 `add_mcp_server` 和 devcontainer 相关方法对 base template 的检查同时接受 `mcp-gateway` / `system/mcp-gateway` 和 `devcontainer` / `system/devcontainer`。替换规则集中在 `scripts/hack.py` 的 `SYSTEM_TEMPLATE_REPLACEMENTS`，每条规则带预期匹配次数，次数不符会直接报错。
- 保留协议 header `E2B-Traffic-Access-Token` 和 `X-E2B-Trace-ID` 不变，因为它们属于服务端兼容协议，不是品牌文案。脚本通过占位符机制保护这些 header。

验证 hack 是否成功时，至少要做下面几类检查：

```bash
# 1. 品牌残留，应该没有输出
rg -n '\bfrom e2b\b|\bimport e2b\b|e2b_code_interpreter|e2b_desktop|E2B_[A-Z0-9_]+|https://e2b\.dev|e2b\.app|e2b-python-sdk|metadata\.version\("e2b"\)|"publisher": "e2b"|api_key="e2b_|UCloud Sandbox Sandbox|UCloud Sandbox cloud sandbox' ucloud_sandbox

# 2. 品牌替换误伤标识符，应该没有输出
rg -n 'class UCloud Sandbox|import UCloud Sandbox|UCloud Sandbox\(' ucloud_sandbox

# 3. 语法
python3 -m compileall -q scripts ucloud_sandbox

# 4. UCloud 定制回归测试
poetry run pytest tests/ -v

# 5. 导入冒烟
poetry run python -c "from ucloud_sandbox import Sandbox, UCloudSandbox; \
from ucloud_sandbox.code_interpreter import Sandbox as CI; \
from ucloud_sandbox.desktop import Sandbox as DT; print('ok')"
```

第一条命令中 `E2B-Traffic-Access-Token` 和 `X-E2B-Trace-ID` 是例外，它们是协议 header，不属于要清理的品牌残留。

文档和 UCloud 专属 helper 也要人工快速过一遍，尤其是 `ucloud_sandbox/__init__.py`、`ucloud_sandbox/client.py`、`ucloud_sandbox/domain_config.py`、`ucloud_sandbox/code_interpreter/*.py`、`ucloud_sandbox/sandbox_sync/main.py`、`ucloud_sandbox/sandbox_async/main.py` 和 `ucloud_sandbox/template/main.py`。目标不是机械替换，而是保证中文或英文文档读起来通顺，避免出现 `UCloud Sandbox Sandbox`、`UCloud Sandbox cloud sandbox` 这类重复或别扭表达。

# 开发注意事项

- 不要把 `upstream/` 当作主要开发目录；它只是上游源码快照。
- **任何 UCloud 定制都必须脚本化到 `scripts/hack.py` 里**。直接手改 `ucloud_sandbox/` 下的文件并提交，看起来能工作，但下一次运行同步脚本就会被上游代码覆盖，而且不会有任何报错提示。调试时可以先手改验证，但提交前一定要把改动搬进 `scripts/hack.py`，再从零跑一遍 `sync_upstreams.sh` + `hack.py` 确认能重建出同样的结果。
- 判断一个定制是否已经脚本化，最直接的办法是在干净工作区跑一遍完整链路，然后 `git diff` —— 应该没有属于 UCloud 定制的内容被还原。
- 如果新增的 UCloud 定制不适合直接写进上游同步文件，优先放到独立 helper 中，并让 `scripts/hack.py` 在同步后可重复创建或恢复它。
- 每次运行 `scripts/sync_upstreams.sh` 后，`ucloud_sandbox/` 会重新变成上游合并结果，之前手动改过但没有脚本化的 UCloud 定制可能会被覆盖；随后需要手动运行 `python3 scripts/hack.py`。
- 如果 `pyproject.toml` 被依赖同步脚本更新了，通常还需要根据需要重新生成 `poetry.lock`。
- `scripts/hack.py` 里大量补丁依赖对上游代码的精确字符串匹配，`replace_once` 在匹配失败时会直接报错。这是有意的：上游一旦改动相关代码，应该立刻暴露出来，而不是静默跳过。升级上游后如果脚本报错，要去对照上游新代码修正锚点，而不是把检查改宽松。

# 上游演进中需要留意的事情

- 上游已经不再提供 vendored 的 `e2b_connect` 包，改用 PyPI 上的 `connectrpc` 和 `pyqwest`；protobuf 运行时也从 `protobuf` 换成了 `protobuf-py`，生成物文件名相应从 `*_pb2.py` 变为 `*_pb.py`（`pyproject.toml` 的 ruff `exclude` 路径需要跟随）。本仓库因此删除了根目录的 `e2b_connect/`。
- 上游已经移除客户端侧的 API key 格式校验，`validate_api_key` 变成 no-op。因此 `UCLOUD_SANDBOX_VALIDATE_API_KEY` 环境变量不再生效，hack 中原本用于关闭校验的补丁也已删除。

# 提交信息规范

- Git commit message 使用 Conventional Commits 风格：`type(scope): summary`。
- 常用 `type` 包括 `feat`、`fix`、`docs`、`test`、`refactor`、`chore`；新增 SDK 能力时优先使用 `feat`。
- `scope` 使用简短英文小写词标识影响范围，例如 `config`、`hack`、`docs`。
- `summary` 用简短英文动词短语，不以句号结尾，例如 `feat(config): add region-based sandbox domain`。
