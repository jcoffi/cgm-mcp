# 🌍 CGM MCP 多语言支持

CGM MCP 现在支持 **28 种编程语言**，共 **55 种文件扩展名**！

## ✅ 支持的编程语言

### 🔥 完全支持（专门分析器）

#### **PHP** 🐘
- **扩展名**: `.php`, `.php3`, `.php4`, `.php5`, `.phtml`
- **支持特性**:
  - ✅ 类 (Classes) - 包括继承和接口实现
  - ✅ 接口 (Interfaces) - 包括继承关系
  - ✅ 特征 (Traits)
  - ✅ 函数 (Functions) - 全局函数
  - ✅ 方法 (Methods) - 类方法，包括可见性
  - ✅ 可见性检测 (public/private/protected)

#### **JavaScript/TypeScript** 🟨
- **扩展名**: `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs`, `.cjs`
- **支持特性**:
  - ✅ ES6 类 (Classes)
  - ✅ 函数声明和表达式
  - ✅ 箭头函数
  - ✅ 异步函数
  - ✅ TypeScript 接口 (仅 .ts/.tsx)
  - ✅ 对象方法

#### **Go** 🐹
- **扩展名**: `.go`
- **支持特性**:
  - ✅ 结构体 (Structs)
  - ✅ 接口 (Interfaces)
  - ✅ 函数 (Functions)
  - ✅ 方法 (Methods)
  - ✅ 包声明

#### **Rust** 🦀
- **扩展名**: `.rs`
- **支持特性**:
  - ✅ 结构体 (Structs)
  - ✅ 枚举 (Enums)
  - ✅ 特征 (Traits)
  - ✅ 函数 (Functions)
  - ✅ 实现块 (Impl blocks)
  - ✅ 可见性 (pub)

#### **Ruby** 💎
- **扩展名**: `.rb`, `.rbw`
- **支持特性**:
  - ✅ 类 (Classes) - 包括继承
  - ✅ 模块 (Modules)
  - ✅ 方法 (Methods)
  - ✅ 实例变量

#### **C#** 🔷
- **扩展名**: `.cs`
- **支持特性**:
  - ✅ 类 (Classes) - 包括继承和接口
  - ✅ 接口 (Interfaces)
  - ✅ 方法 (Methods)
  - ✅ 属性 (Properties)
  - ✅ 命名空间 (Namespaces)
  - ✅ 可见性修饰符

#### **Java/Kotlin/Scala** ☕
- **扩展名**: `.java`, `.kt`, `.scala`
- **支持特性**:
  - ✅ 类 (Classes)
  - ✅ 接口 (Interfaces)
  - ✅ 枚举 (Enums)
  - ✅ 方法 (Methods)
  - ✅ 包声明

#### **C/C++** ⚡
- **扩展名**: `.c`, `.cpp`, `.cc`, `.cxx`, `.h`, `.hpp`, `.hxx`
- **支持特性**:
  - ✅ 函数 (Functions)
  - ✅ 结构体 (Structs)
  - ✅ 类 (Classes) - C++ 专用
  - ✅ 命名空间 (Namespaces) - C++ 专用

#### **Python** 🐍
- **扩展名**: `.py`, `.pyx`, `.pyi`
- **支持特性**:
  - ✅ 类 (Classes) - AST 解析
  - ✅ 函数 (Functions) - AST 解析
  - ✅ 方法 (Methods) - AST 解析
  - ✅ 导入语句 - AST 解析
  - ✅ 文档字符串
  - ✅ 装饰器

### 🔧 基础支持（通用分析器）

以下语言通过通用模式匹配支持基本的函数和类识别：

- **Swift** (`.swift`)
- **Objective-C** (`.m`, `.mm`)
- **Dart** (`.dart`)
- **Lua** (`.lua`)
- **Shell** (`.sh`, `.bash`, `.zsh`, `.fish`)
- **SQL** (`.sql`)
- **R** (`.r`, `.R`)
- **Perl** (`.pl`, `.pm`)
- **Haskell** (`.hs`)
- **Erlang** (`.erl`)
- **Elixir** (`.ex`, `.exs`)
- **Clojure** (`.clj`, `.cljs`, `.cljc`)
- **F#** (`.fs`, `.fsx`)
- **Visual Basic** (`.vb`)
- **PowerShell** (`.ps1`, `.psm1`)

## 📊 测试结果

```
🔍 Testing PHP analysis...
   📊 Found 9 entities:
      file: test.php
      class: UserController
      function: login, authenticate, getUser, log, validateEmail
      interface: UserInterface
      trait: Loggable
   ✅ PHP analysis completed

🔍 Testing JS analysis...
   📊 Found 5 entities:
      file: test.js
      class: UserManager
      function: validateUser, authenticate, createUser
   ✅ JS analysis completed

🔍 Testing GO analysis...
   📊 Found 6 entities:
      file: test.go
      function: GetUser, main
      struct: User, UserRepository
      interface: UserService
   ✅ GO analysis completed

🔍 Testing RS analysis...
   📊 Found 10 entities:
      file: test.rs
      function: get_user, new, get_user, create_user, validate_email
      struct: User, UserRepository
      enum: UserError
      trait: UserService
   ✅ RS analysis completed

🔍 Testing RB analysis...
   📊 Found 11 entities:
      file: test.rb
      class: User, UserService
      module: UserValidation
      method: initialize, to_s, validate_email, validate_username, initialize
   ✅ RB analysis completed

🔍 Testing CS analysis...
   📊 Found 12 entities:
      file: test.cs
      class: User, UserService, UserHelper
      interface: IUserService
      method: User, ToString, UserService, GetUser, CreateUser
   ✅ CS analysis completed
```

## 🚀 使用示例

### 分析 PHP 项目
```python
from cgm_mcp.models import CodeAnalysisRequest

request = CodeAnalysisRequest(
    repository_path="/path/to/php/project",
    query="authentication system",
    analysis_scope="focused"
)

response = await analyzer.analyze_repository(request)
```

### 通过 MCP 工具调用
```json
{
  "tool": "cgm_analyze_repository",
  "arguments": {
    "repository_path": "/path/to/project",
    "query": "user management",
    "analysis_scope": "focused"
  }
}
```

## 🔧 扩展新语言

要添加对新语言的支持，只需：

1. **添加文件扩展名**:
```python
self.supported_extensions.add(".new_ext")
```

2. **添加语言检测**:
```python
".new_ext": "new_language"
```

3. **创建专门分析器**（可选）:
```python
def _analyze_new_language_file(self, content: str, file_path: str) -> List[CodeEntity]:
    # 实现语言特定的分析逻辑
    pass
```

## 🎯 语言特性支持矩阵

| 语言 | 类/结构体 | 接口 | 函数/方法 | 继承 | 可见性 | 特殊特性 |
|------|-----------|------|-----------|------|--------|----------|
| PHP | ✅ | ✅ | ✅ | ✅ | ✅ | Traits |
| JavaScript | ✅ | ✅* | ✅ | ✅ | ❌ | Arrow Functions |
| TypeScript | ✅ | ✅ | ✅ | ✅ | ✅ | Type Annotations |
| Go | ✅ | ✅ | ✅ | ❌ | ✅ | Packages |
| Rust | ✅ | ✅ | ✅ | ❌ | ✅ | Traits, Enums |
| Ruby | ✅ | ❌ | ✅ | ✅ | ❌ | Modules |
| C# | ✅ | ✅ | ✅ | ✅ | ✅ | Namespaces |
| Java | ✅ | ✅ | ✅ | ✅ | ✅ | Packages |
| C/C++ | ✅ | ❌ | ✅ | ✅ | ✅ | Namespaces |
| Python | ✅ | ❌ | ✅ | ✅ | ❌ | Decorators |

*仅 TypeScript

## 🔮 未来计划

- [ ] 添加更多语言的专门分析器
- [ ] 支持语言特定的依赖关系分析
- [ ] 增强跨语言项目支持
- [ ] 添加语法高亮和代码格式化
- [ ] 支持更复杂的代码结构分析

---

**CGM MCP 现在是真正的多语言代码分析工具！** 🌍✨
