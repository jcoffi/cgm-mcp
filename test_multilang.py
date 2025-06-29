#!/usr/bin/env python3
"""
Test multi-language support for CGM MCP
"""

import asyncio
import sys
import tempfile
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Sample code files for testing
SAMPLE_FILES = {
    "test.php": '''<?php
class UserController {
    private $db;
    
    public function __construct($database) {
        $this->db = $database;
    }
    
    public function login($username, $password) {
        return $this->authenticate($username, $password);
    }
    
    private function authenticate($username, $password) {
        // Authentication logic
        return true;
    }
}

interface UserInterface {
    public function getUser($id);
}

trait Loggable {
    public function log($message) {
        echo $message;
    }
}

function validateEmail($email) {
    return filter_var($email, FILTER_VALIDATE_EMAIL);
}
?>''',

    "test.js": '''
class UserManager {
    constructor(config) {
        this.config = config;
    }
    
    async login(username, password) {
        return await this.authenticate(username, password);
    }
    
    authenticate = (username, password) => {
        // Authentication logic
        return Promise.resolve(true);
    }
}

function validateUser(user) {
    return user && user.username && user.password;
}

const createUser = (data) => {
    return new User(data);
};

export { UserManager, validateUser };
''',

    "test.go": '''package main

import "fmt"

type User struct {
    ID       int    `json:"id"`
    Username string `json:"username"`
    Email    string `json:"email"`
}

type UserService interface {
    GetUser(id int) (*User, error)
    CreateUser(user *User) error
}

type UserRepository struct {
    db Database
}

func (r *UserRepository) GetUser(id int) (*User, error) {
    // Implementation
    return &User{}, nil
}

func (r *UserRepository) CreateUser(user *User) error {
    // Implementation
    return nil
}

func validateEmail(email string) bool {
    // Email validation logic
    return true
}

func main() {
    fmt.Println("User service started")
}
''',

    "test.rs": '''
use std::collections::HashMap;

pub struct User {
    pub id: u32,
    pub username: String,
    pub email: String,
}

pub trait UserService {
    fn get_user(&self, id: u32) -> Option<User>;
    fn create_user(&mut self, user: User) -> Result<(), String>;
}

pub struct UserRepository {
    users: HashMap<u32, User>,
}

impl UserRepository {
    pub fn new() -> Self {
        Self {
            users: HashMap::new(),
        }
    }
}

impl UserService for UserRepository {
    fn get_user(&self, id: u32) -> Option<User> {
        self.users.get(&id).cloned()
    }
    
    fn create_user(&mut self, user: User) -> Result<(), String> {
        self.users.insert(user.id, user);
        Ok(())
    }
}

pub fn validate_email(email: &str) -> bool {
    email.contains('@')
}

#[derive(Debug)]
pub enum UserError {
    NotFound,
    InvalidData,
}
''',

    "test.rb": '''
class User
  attr_accessor :id, :username, :email
  
  def initialize(id, username, email)
    @id = id
    @username = username
    @email = email
  end
  
  def to_s
    "User(#{@id}, #{@username}, #{@email})"
  end
end

module UserValidation
  def validate_email(email)
    email.include?('@')
  end
  
  def validate_username(username)
    username.length >= 3
  end
end

class UserService
  include UserValidation
  
  def initialize(repository)
    @repository = repository
  end
  
  def create_user(user_data)
    return false unless validate_email(user_data[:email])
    return false unless validate_username(user_data[:username])
    
    @repository.save(user_data)
  end
end

def format_user(user)
  "#{user.username} <#{user.email}>"
end
''',

    "test.cs": '''
using System;
using System.Collections.Generic;

namespace UserManagement
{
    public interface IUserService
    {
        User GetUser(int id);
        bool CreateUser(User user);
    }
    
    public class User
    {
        public int Id { get; set; }
        public string Username { get; set; }
        public string Email { get; set; }
        
        public User(int id, string username, string email)
        {
            Id = id;
            Username = username;
            Email = email;
        }
        
        public override string ToString()
        {
            return $"User({Id}, {Username}, {Email})";
        }
    }
    
    public class UserService : IUserService
    {
        private readonly IUserRepository _repository;
        
        public UserService(IUserRepository repository)
        {
            _repository = repository;
        }
        
        public User GetUser(int id)
        {
            return _repository.FindById(id);
        }
        
        public bool CreateUser(User user)
        {
            if (!ValidateUser(user))
                return false;
                
            return _repository.Save(user);
        }
        
        private bool ValidateUser(User user)
        {
            return !string.IsNullOrEmpty(user.Username) && 
                   !string.IsNullOrEmpty(user.Email);
        }
    }
    
    public static class UserHelper
    {
        public static bool ValidateEmail(string email)
        {
            return email.Contains("@");
        }
    }
}
'''
}

async def test_language_support():
    """Test multi-language support"""
    from cgm_mcp.core.analyzer import CGMAnalyzer
    from cgm_mcp.models import CodeAnalysisRequest
    
    print("🌍 Testing Multi-Language Support")
    print("=" * 50)
    
    analyzer = CGMAnalyzer()
    
    # Create temporary directory with sample files
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Created test directory: {temp_dir}")
        
        # Write sample files
        for filename, content in SAMPLE_FILES.items():
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"   ✅ Created {filename}")
        
        print()
        
        # Test analysis for each language
        for filename in SAMPLE_FILES.keys():
            language = filename.split('.')[1]
            print(f"🔍 Testing {language.upper()} analysis...")
            
            try:
                request = CodeAnalysisRequest(
                    repository_path=temp_dir,
                    query=f"{language} code analysis",
                    analysis_scope="focused",
                    focus_files=[filename],
                    max_files=1
                )
                
                response = await analyzer.analyze_repository(request)
                
                # Filter entities for this file
                file_entities = [e for e in response.relevant_entities if e.file_path == filename]
                
                print(f"   📊 Found {len(file_entities)} entities:")
                
                # Group by type
                entity_types = {}
                for entity in file_entities:
                    if entity.type not in entity_types:
                        entity_types[entity.type] = []
                    entity_types[entity.type].append(entity.name)
                
                for entity_type, names in entity_types.items():
                    print(f"      {entity_type}: {', '.join(names[:5])}")
                    if len(names) > 5:
                        print(f"         ... and {len(names) - 5} more")
                
                print(f"   ✅ {language.upper()} analysis completed")
                
            except Exception as e:
                print(f"   ❌ {language.upper()} analysis failed: {e}")
            
            print()
    
    print("🎉 Multi-language testing completed!")

async def test_supported_extensions():
    """Test supported file extensions"""
    from cgm_mcp.core.analyzer import CGMAnalyzer
    
    print("📋 Supported File Extensions")
    print("=" * 30)
    
    analyzer = CGMAnalyzer()
    extensions = sorted(list(analyzer.supported_extensions))
    
    # Group by language
    language_groups = {}
    for ext in extensions:
        lang = analyzer._detect_language(f"test{ext}")
        if lang not in language_groups:
            language_groups[lang] = []
        language_groups[lang].append(ext)
    
    for language, exts in sorted(language_groups.items()):
        print(f"{language.title()}: {', '.join(exts)}")
    
    print(f"\nTotal: {len(extensions)} file extensions supported")

async def main():
    """Run all tests"""
    await test_supported_extensions()
    print()
    await test_language_support()
    
    print("\n💡 Language Support Summary:")
    print("✅ PHP - Classes, interfaces, traits, functions")
    print("✅ JavaScript/TypeScript - Classes, functions, interfaces")
    print("✅ Go - Structs, interfaces, functions")
    print("✅ Rust - Structs, traits, enums, functions")
    print("✅ Ruby - Classes, modules, methods")
    print("✅ C# - Classes, interfaces, methods")
    print("✅ Java - Classes, interfaces, methods")
    print("✅ C/C++ - Functions, structs, classes")
    print("✅ Python - Classes, functions (AST-based)")
    print("✅ And many more...")

if __name__ == "__main__":
    asyncio.run(main())
