#!/usr/bin/env python3
"""
Performance test for CGM MCP Server optimizations
"""

import asyncio
import time
import sys
import statistics
from pathlib import Path
import tempfile
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cgm_mcp.server_modelless import ModellessCGMServer
from cgm_mcp.server_modelless_optimized import OptimizedModellessCGMServer
from cgm_mcp.utils.config import Config


# Sample test files
TEST_FILES = {
    "large_python.py": '''
class UserManager:
    """Large Python file for testing"""
    
    def __init__(self, database):
        self.db = database
        self.cache = {}
        
    def get_user(self, user_id):
        if user_id in self.cache:
            return self.cache[user_id]
        user = self.db.get_user(user_id)
        self.cache[user_id] = user
        return user
        
    def create_user(self, user_data):
        user = User(**user_data)
        self.db.save(user)
        return user
        
    def update_user(self, user_id, updates):
        user = self.get_user(user_id)
        for key, value in updates.items():
            setattr(user, key, value)
        self.db.save(user)
        return user
        
    def delete_user(self, user_id):
        if user_id in self.cache:
            del self.cache[user_id]
        self.db.delete_user(user_id)
        
    def list_users(self, filters=None):
        return self.db.list_users(filters)
        
    def authenticate(self, username, password):
        user = self.db.get_user_by_username(username)
        if user and user.check_password(password):
            return user
        return None
        
    def change_password(self, user_id, old_password, new_password):
        user = self.get_user(user_id)
        if user.check_password(old_password):
            user.set_password(new_password)
            self.db.save(user)
            return True
        return False

class User:
    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password_hash = self.hash_password(password)
        
    def hash_password(self, password):
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()
        
    def check_password(self, password):
        return self.password_hash == self.hash_password(password)
        
    def set_password(self, password):
        self.password_hash = self.hash_password(password)

class Database:
    def __init__(self):
        self.users = {}
        self.next_id = 1
        
    def get_user(self, user_id):
        return self.users.get(user_id)
        
    def get_user_by_username(self, username):
        for user in self.users.values():
            if user.username == username:
                return user
        return None
        
    def save(self, user):
        if not hasattr(user, 'id'):
            user.id = self.next_id
            self.next_id += 1
        self.users[user.id] = user
        
    def delete_user(self, user_id):
        if user_id in self.users:
            del self.users[user_id]
            
    def list_users(self, filters=None):
        users = list(self.users.values())
        if filters:
            # Apply filters
            pass
        return users
''',
    
    "complex_js.js": '''
class APIClient {
    constructor(baseURL, apiKey) {
        this.baseURL = baseURL;
        this.apiKey = apiKey;
        this.cache = new Map();
    }
    
    async request(method, endpoint, data = null) {
        const url = `${this.baseURL}${endpoint}`;
        const options = {
            method,
            headers: {
                'Authorization': `Bearer ${this.apiKey}`,
                'Content-Type': 'application/json'
            }
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, options);
        return await response.json();
    }
    
    async get(endpoint) {
        const cacheKey = `GET:${endpoint}`;
        if (this.cache.has(cacheKey)) {
            return this.cache.get(cacheKey);
        }
        
        const result = await this.request('GET', endpoint);
        this.cache.set(cacheKey, result);
        return result;
    }
    
    async post(endpoint, data) {
        return await this.request('POST', endpoint, data);
    }
    
    async put(endpoint, data) {
        return await this.request('PUT', endpoint, data);
    }
    
    async delete(endpoint) {
        return await this.request('DELETE', endpoint);
    }
}

function createUserService(apiClient) {
    return {
        async getUser(id) {
            return await apiClient.get(`/users/${id}`);
        },
        
        async createUser(userData) {
            return await apiClient.post('/users', userData);
        },
        
        async updateUser(id, updates) {
            return await apiClient.put(`/users/${id}`, updates);
        },
        
        async deleteUser(id) {
            return await apiClient.delete(`/users/${id}`);
        }
    };
}

const utils = {
    validateEmail: (email) => {
        const regex = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
        return regex.test(email);
    },
    
    generateId: () => {
        return Math.random().toString(36).substr(2, 9);
    },
    
    formatDate: (date) => {
        return new Intl.DateTimeFormat('en-US').format(date);
    }
};
''',
    
    "service.go": '''
package main

import (
    "fmt"
    "time"
    "sync"
)

type User struct {
    ID       int       `json:"id"`
    Username string    `json:"username"`
    Email    string    `json:"email"`
    Created  time.Time `json:"created"`
}

type UserService struct {
    users map[int]*User
    mutex sync.RWMutex
    nextID int
}

func NewUserService() *UserService {
    return &UserService{
        users: make(map[int]*User),
        nextID: 1,
    }
}

func (s *UserService) CreateUser(username, email string) (*User, error) {
    s.mutex.Lock()
    defer s.mutex.Unlock()
    
    user := &User{
        ID:       s.nextID,
        Username: username,
        Email:    email,
        Created:  time.Now(),
    }
    
    s.users[user.ID] = user
    s.nextID++
    
    return user, nil
}

func (s *UserService) GetUser(id int) (*User, error) {
    s.mutex.RLock()
    defer s.mutex.RUnlock()
    
    user, exists := s.users[id]
    if !exists {
        return nil, fmt.Errorf("user not found")
    }
    
    return user, nil
}

func (s *UserService) UpdateUser(id int, username, email string) error {
    s.mutex.Lock()
    defer s.mutex.Unlock()
    
    user, exists := s.users[id]
    if !exists {
        return fmt.Errorf("user not found")
    }
    
    user.Username = username
    user.Email = email
    
    return nil
}

func (s *UserService) DeleteUser(id int) error {
    s.mutex.Lock()
    defer s.mutex.Unlock()
    
    _, exists := s.users[id]
    if !exists {
        return fmt.Errorf("user not found")
    }
    
    delete(s.users, id)
    return nil
}

func (s *UserService) ListUsers() []*User {
    s.mutex.RLock()
    defer s.mutex.RUnlock()
    
    users := make([]*User, 0, len(s.users))
    for _, user := range s.users {
        users = append(users, user)
    }
    
    return users
}
'''
}


async def benchmark_server(server_class, server_name, test_dir, num_requests=10):
    """Benchmark a server implementation"""
    print(f"\n🧪 Benchmarking {server_name}")
    print("=" * 50)
    
    config = Config.load()
    server = server_class(config)
    
    # Test arguments
    test_args = {
        "repository_path": test_dir,
        "query": "user management system",
        "analysis_scope": "focused",
        "max_files": 5
    }
    
    times = []
    cache_hits = 0
    
    for i in range(num_requests):
        start_time = time.time()
        
        try:
            result = await server._analyze_repository_optimized(test_args) if hasattr(server, '_analyze_repository_optimized') else await server._analyze_repository(test_args)
            
            end_time = time.time()
            request_time = end_time - start_time
            times.append(request_time)
            
            # Check if it was a cache hit
            if result.get("cached", False) or "cache_key" in result:
                cache_hits += 1
                
            print(f"  Request {i+1:2d}: {request_time:.3f}s {'(cached)' if result.get('cached', False) else ''}")
            
        except Exception as e:
            print(f"  Request {i+1:2d}: FAILED - {e}")
            
    # Calculate statistics
    if times:
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        median_time = statistics.median(times)
        
        print(f"\n📊 Results for {server_name}:")
        print(f"  Total requests: {len(times)}")
        print(f"  Cache hits: {cache_hits}")
        print(f"  Average time: {avg_time:.3f}s")
        print(f"  Median time: {median_time:.3f}s")
        print(f"  Min time: {min_time:.3f}s")
        print(f"  Max time: {max_time:.3f}s")
        print(f"  Requests/sec: {len(times) / sum(times):.2f}")
        
        if hasattr(server, 'performance_monitor'):
            stats = server.performance_monitor.get_stats()
            print(f"  Memory usage: {stats.get('current_memory_mb', 0):.1f}MB")
            
        if hasattr(server, 'cache'):
            print(f"  Cache size: {server.cache.size()}")
            
    # Cleanup
    if hasattr(server, 'cleanup'):
        await server.cleanup()
        
    return {
        "server_name": server_name,
        "times": times,
        "cache_hits": cache_hits,
        "avg_time": avg_time if times else 0,
        "requests_per_second": len(times) / sum(times) if times else 0
    }


async def test_concurrent_requests(server_class, server_name, test_dir, num_concurrent=5):
    """Test concurrent request handling"""
    print(f"\n🔄 Testing concurrent requests for {server_name}")
    print("=" * 50)
    
    config = Config.load()
    server = server_class(config)
    
    test_args = {
        "repository_path": test_dir,
        "query": "concurrent test",
        "analysis_scope": "minimal",
        "max_files": 3
    }
    
    # Create concurrent tasks
    tasks = []
    for i in range(num_concurrent):
        task_args = {**test_args, "query": f"concurrent test {i}"}
        if hasattr(server, '_analyze_repository_optimized'):
            task = asyncio.create_task(server._analyze_repository_optimized(task_args))
        else:
            task = asyncio.create_task(server._analyze_repository(task_args))
        tasks.append(task)
    
    start_time = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    end_time = time.time()
    
    total_time = end_time - start_time
    successful_requests = sum(1 for r in results if not isinstance(r, Exception))
    
    print(f"  Concurrent requests: {num_concurrent}")
    print(f"  Successful: {successful_requests}")
    print(f"  Total time: {total_time:.3f}s")
    print(f"  Requests/sec: {successful_requests / total_time:.2f}")
    
    # Cleanup
    if hasattr(server, 'cleanup'):
        await server.cleanup()
    
    return {
        "concurrent_requests": num_concurrent,
        "successful": successful_requests,
        "total_time": total_time,
        "requests_per_second": successful_requests / total_time
    }


async def main():
    """Run performance tests"""
    print("🚀 CGM MCP Server Performance Tests")
    print("=" * 60)
    
    # Create test directory with sample files
    with tempfile.TemporaryDirectory() as test_dir:
        print(f"📁 Created test directory: {test_dir}")
        
        # Write test files
        for filename, content in TEST_FILES.items():
            file_path = os.path.join(test_dir, filename)
            with open(file_path, 'w') as f:
                f.write(content)
            print(f"   ✅ Created {filename}")
        
        # Test original server
        original_results = await benchmark_server(
            ModellessCGMServer, 
            "Original Server", 
            test_dir, 
            num_requests=5
        )
        
        # Test optimized server
        optimized_results = await benchmark_server(
            OptimizedModellessCGMServer, 
            "Optimized Server", 
            test_dir, 
            num_requests=5
        )
        
        # Test concurrent requests
        print("\n" + "=" * 60)
        original_concurrent = await test_concurrent_requests(
            ModellessCGMServer,
            "Original Server",
            test_dir,
            num_concurrent=3
        )
        
        optimized_concurrent = await test_concurrent_requests(
            OptimizedModellessCGMServer,
            "Optimized Server", 
            test_dir,
            num_concurrent=3
        )
        
        # Performance comparison
        print("\n" + "=" * 60)
        print("📈 Performance Comparison")
        print("=" * 60)
        
        if original_results["avg_time"] > 0 and optimized_results["avg_time"] > 0:
            speedup = original_results["avg_time"] / optimized_results["avg_time"]
            print(f"Average response time improvement: {speedup:.2f}x")
            
        if original_results["requests_per_second"] > 0 and optimized_results["requests_per_second"] > 0:
            throughput_improvement = optimized_results["requests_per_second"] / original_results["requests_per_second"]
            print(f"Throughput improvement: {throughput_improvement:.2f}x")
            
        print(f"Cache hits (optimized): {optimized_results['cache_hits']}")
        
        print(f"\nConcurrent performance:")
        if original_concurrent["requests_per_second"] > 0 and optimized_concurrent["requests_per_second"] > 0:
            concurrent_improvement = optimized_concurrent["requests_per_second"] / original_concurrent["requests_per_second"]
            print(f"Concurrent throughput improvement: {concurrent_improvement:.2f}x")
        
        print("\n🎉 Performance testing completed!")
        print("\n💡 Optimization benefits:")
        print("  • LRU caching reduces repeated analysis")
        print("  • Request deduplication prevents duplicate work")
        print("  • Concurrent processing improves throughput")
        print("  • Memory monitoring prevents resource exhaustion")
        print("  • Background maintenance keeps performance stable")


if __name__ == "__main__":
    asyncio.run(main())
