# 🌍 CGM MCP Multi-Language Support

CGM MCP now supports **28 programming languages** with **55 file extensions**!

## ✅ Supported Programming Languages

### 🔥 Full Support (Dedicated Analyzers)

#### **PHP** 🐘
- **Extensions**: `.php`, `.php3`, `.php4`, `.php5`, `.phtml`
- **Supported Features**:
  - ✅ Classes - including inheritance and interface implementation
  - ✅ Interfaces - including inheritance relationships
  - ✅ Traits
  - ✅ Functions - global functions
  - ✅ Methods - class methods, including visibility
  - ✅ Visibility detection (public/private/protected)

#### **JavaScript/TypeScript** 🟨
- **Extensions**: `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs`, `.cjs`
- **Supported Features**:
  - ✅ ES6 Classes
  - ✅ Function declarations and expressions
  - ✅ Arrow functions
  - ✅ Async functions
  - ✅ TypeScript interfaces (TypeScript files only)
  - ✅ Object methods

#### **Go** 🐹
- **Extensions**: `.go`
- **Supported Features**:
  - ✅ Structs
  - ✅ Interfaces
  - ✅ Functions
  - ✅ Methods
  - ✅ Package declarations

#### **Rust** 🦀
- **Extensions**: `.rs`
- **Supported Features**:
  - ✅ Structs
  - ✅ Enums
  - ✅ Traits
  - ✅ Functions
  - ✅ Implementation blocks (Impl blocks)
  - ✅ Visibility (pub)

#### **Ruby** 💎
- **Extensions**: `.rb`, `.rbw`
- **Supported Features**:
  - ✅ Classes - including inheritance
  - ✅ Modules
  - ✅ Methods
  - ✅ Instance variables

#### **C#** 🔷
- **Extensions**: `.cs`
- **Supported Features**:
  - ✅ Classes - including inheritance and interfaces
  - ✅ Interfaces
  - ✅ Methods
  - ✅ Properties
  - ✅ Namespaces
  - ✅ Visibility modifiers

#### **Java/Kotlin/Scala** ☕
- **Extensions**: `.java`, `.kt`, `.scala`
- **Supported Features**:
  - ✅ Classes
  - ✅ Interfaces
  - ✅ Enums
  - ✅ Methods
  - ✅ Package declarations

#### **C/C++** ⚡
- **Extensions**: `.c`, `.cpp`, `.cc`, `.cxx`, `.h`, `.hpp`, `.hxx`
- **Supported Features**:
  - ✅ Functions
  - ✅ Structs
  - ✅ Classes (C++ only)
  - ✅ Namespaces (C++ only)

#### **Python** 🐍
- **Extensions**: `.py`, `.pyx`, `.pyi`
- **Supported Features**:
  - ✅ Classes - AST parsing
  - ✅ Functions - AST parsing
  - ✅ Methods - AST parsing
  - ✅ Import statements - AST parsing
  - ✅ Docstrings
  - ✅ Decorators

### 🔧 Basic Support (Generic Analyzer)

The following languages are supported through generic pattern matching for basic function and class recognition:

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

## 📊 Test Results

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

## 🚀 Usage Examples

### Analyzing PHP Projects
```python
from cgm_mcp.models import CodeAnalysisRequest

request = CodeAnalysisRequest(
    repository_path="/path/to/php/project",
    query="authentication system",
    analysis_scope="focused"
)

response = await analyzer.analyze_repository(request)
```

### Using MCP Tool Calls
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

## 🔧 Adding New Language Support

To add support for a new language:

1. **Add file extension**:
```python
self.supported_extensions.add(".new_ext")
```

2. **Add language detection**:
```python
".new_ext": "new_language"
```

3. **Create dedicated analyzer** (optional):
```python
def _analyze_new_language_file(self, content: str, file_path: str) -> List[CodeEntity]:
    # Implement language-specific analysis logic
    pass
```

## 🎯 Language Feature Support Matrix

| Language | Classes/Structs | Interfaces | Functions/Methods | Inheritance | Visibility | Special Features |
|----------|-----------------|------------|-------------------|-------------|------------|------------------|
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

*TypeScript only

## 🔮 Future Plans

- [ ] Add more dedicated analyzers for additional languages
- [ ] Support language-specific dependency analysis
- [ ] Enhance cross-language project support
- [ ] Add syntax highlighting and code formatting
- [ ] Support more complex code structure analysis

---

**CGM MCP is now a truly multi-language code analysis tool!** 🌍✨
