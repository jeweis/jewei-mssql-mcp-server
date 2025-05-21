# Jewei MSSQL MCP 服务器

## 项目简介

这是一个基于FastMCP框架开发的MCP服务器，专门用于执行Microsoft SQL Server的数据查询和表结构查询操作。该服务器提供了一系列工具，使客户端能够方便地与SQL Server数据库进行交互。

## 功能特点

- **数据查询**：执行SQL查询并返回结果集
- **表结构查询**：获取数据库表的结构信息
- **简单易用**：通过MCP协议提供标准化的接口
- **高效可靠**：优化的数据库连接管理

## 技术架构

本项目基于以下技术构建：

- **FastMCP**：一个用于构建MCP服务器的Python框架
- **Python**：主要开发语言
- **Microsoft SQL Server**：目标数据库系统
- **MCP协议**：用于客户端与服务器之间的通信

## 安装与配置

### 前提条件

- Python 3.7+
- 访问Microsoft SQL Server的权限
- FastMCP库

### 安装步骤

1. 克隆本仓库
   ```bash
   git clone [仓库URL]
   cd jewei-mssql-mcp-server
   ```

2. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

3. 配置数据库连接
   - 创建配置文件或设置环境变量（具体配置方法见下文）

## 使用方法

### 启动服务器

```bash
python server.py
```

默认情况下，服务器使用STDIO传输机制。如需使用HTTP传输，可修改`server.py`中的相关配置。

### 客户端调用示例

使用任何支持MCP协议的客户端都可以连接到此服务器。以下是一个基本的调用示例：

```python
from fastmcp import Client

# 连接到MCP服务器
client = Client("http://localhost:9000")

# 执行SQL查询
result = client.call("query_sql", sql="SELECT * FROM users LIMIT 10")
print(result)

# 获取表结构
structure = client.call("get_table_structure", table_name="users")
print(structure)
```

## 配置选项

服务器配置可以通过以下方式设置：

1. 环境变量
2. 配置文件
3. 直接在代码中设置
4. 通过uv配置MCP服务器

### 使用uv安装和管理依赖

本项目支持使用uv（一个快速的Python包管理器）来安装和管理依赖。使用uv可以显著提高包安装速度并确保环境一致性。

首先安装uv：

```bash
# 安装uv
pip install uv
```

然后使用uv创建虚拟环境并安装依赖：

```bash
# 创建虚拟环境
uv venv

# 激活虚拟环境
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# 使用uv安装依赖
uv pip install -r requirements.txt
```

安装完成后，您可以通过以下方式启动MCP服务器：

```bash
python server.py
```

您也可以在`~/.codeium/windsurf/mcp_config.json`文件中配置服务器，以便与Cascade集成。本项目支持使用uvx命令来配置MCP服务器：

```json
{
  "mcpServers": {
    "jewei-mssql": {
      "disabled": false,
      "command": "uvx",
      "args": [
        "jewei-mssql-mcp-server"
      ],
      "env": {
        "DB_HOST": "your_db_host",
        "DB_USER": "your_db_user",
        "DB_PASSWORD": "your_db_password",
        "DB_NAME": "your_db_name"
      }
    }
  }
}
```

其中，`uvx`是用于运行已安装的Python包的命令，`jewei-mssql-mcp-server`是包名。这种方式可以确保使用正确的环境运行MCP服务器。

### 主要配置项

主要配置项包括：

- 数据库连接信息（服务器地址、用户名、密码、数据库名）
- 服务器监听地址和端口
- 日志级别

## 贡献指南

欢迎贡献代码或提出改进建议！请遵循以下步骤：

1. Fork本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 许可证

[指定许可证类型]

## 联系方式

如有问题或建议，请联系[联系人信息]。
