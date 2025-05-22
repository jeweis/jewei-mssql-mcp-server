# 使用uv发布到PyPI的指南

本文档提供了使用uv工具将`jewei-mssql-mcp-server`包发布到PyPI的详细步骤。

## 前提条件

1. 安装uv工具
   ```bash
   pip install uv
   ```

2. 确保你有PyPI账号，并且已经创建了API令牌
   - 访问 https://pypi.org/manage/account/token/ 创建令牌
   - 保存令牌，它只会显示一次

## 发布步骤

### 1. 构建分发包

```bash
uv build
```

这将在`dist/`目录下创建源代码分发包(.tar.gz)和轮子分发包(.whl)。

### 2. 检查分发包

```bash
uv check dist/*
```

### 3. 上传到PyPI

```bash
uv publish
```

系统会提示你输入PyPI用户名和密码或API令牌。

### 4. 验证发布

发布完成后，访问 https://pypi.org/project/jewei-mssql-mcp-server/ 确认包已成功发布。

## 版本更新

当需要发布新版本时，请按照以下步骤操作：

1. 在`pyproject.toml`文件中更新版本号
2. 更新CHANGELOG.md（如果有）
3. 提交更改并打标签
4. 按照上述步骤构建并发布新版本

## 注意事项

- 确保`pyproject.toml`中的版本号与你要发布的版本一致
- 确保所有依赖项都正确声明
- 发布前测试包的安装和功能
- 使用`uv build --sdist --wheel`可以同时构建源代码分发包和轮子分发包