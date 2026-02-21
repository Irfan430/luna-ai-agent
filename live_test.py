"""
LUNA AI Agent - Live Integration Test
Tests the core components with real API calls.
"""
import os
import yaml
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("luna.live_test")

def load_config():
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    # Override to use openai provider for testing in this environment
    config["llm"]["default_provider"] = "openai"
    # Use environment variable for testing if config key is placeholder
    if config["llm"]["providers"]["openai"]["api_key"].startswith("your-"):
        config["llm"]["providers"]["openai"]["api_key"] = os.getenv("OPENAI_API_KEY", "your-openai-api-key-here")
    return config

def test_memory_system(config):
    print("\n--- Testing Memory System ---")
    from memory.system import MemorySystem
    mem = MemorySystem(config)
    mem.add_short_term("user", "Hello, LUNA!")
    mem.add_short_term("assistant", "Hello! How can I help?")
    assert len(mem.short_term) == 2
    summary = mem.get_summarized_history()
    assert "Hello, LUNA!" in summary
    print("Memory System: PASSED")
    return True

def test_llm_router(config):
    print("\n--- Testing LLM Router (Live API Call) ---")
    from llm.provider import LLMManager
    from llm.router import LLMRouter
    
    manager = LLMManager(config)
    if not manager.providers:
        print("LLM Router: SKIPPED (No providers configured)")
        return True
    
    router = LLMRouter(manager, config)
    result = router.route("What is 2 + 2?")
    print(f"  Intent: {result.intent}")
    print(f"  Response: {result.response[:100]}")
    assert result.intent in ["conversation", "system_command", "browser_task", "file_operation", "app_control", "code"]
    print("LLM Router: PASSED")
    return True

def test_execution_kernel(config):
    print("\n--- Testing Execution Kernel ---")
    from execution.kernel import ExecutionKernel
    kernel = ExecutionKernel(config)
    
    result = kernel.execute("system", {"command": "echo 'LUNA kernel test'"})
    print(f"  Status: {result.status}, Content: {result.content.strip()}")
    assert result.status == "success"
    assert "LUNA kernel test" in result.content
    
    result_file = kernel.execute("file", {"op": "create", "path": "/tmp/luna_test.txt", "content": "test"})
    assert result_file.status == "success"
    
    result_read = kernel.execute("file", {"op": "read", "path": "/tmp/luna_test.txt"})
    assert result_read.status == "success"
    assert result_read.content == "test"
    
    kernel.execute("file", {"op": "delete", "path": "/tmp/luna_test.txt"})
    
    print("Execution Kernel: PASSED")
    kernel.browser_controller.close()
    return True

def test_voice_engine(config):
    print("\n--- Testing Voice Engine ---")
    from voice.engine import VoiceEngine
    voice = VoiceEngine(config)
    assert not voice.enabled
    assert isinstance(voice.acknowledgment_phrases, list)
    assert len(voice.acknowledgment_phrases) > 0
    assert not voice.passive_listening_enabled
    print("Voice Engine: PASSED")
    return True

def test_task_result():
    print("\n--- Testing TaskResult ---")
    from core.task_result import TaskResult
    
    r = TaskResult.failure("test error")
    assert r.status == "failed"
    assert r.error == "test error"
    
    r2 = TaskResult.success("test content")
    assert r2.status == "success"
    assert r2.verified == True
    
    print("TaskResult: PASSED")
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("LUNA AI Agent - Live Integration Test")
    print("=" * 50)
    
    config = load_config()
    
    results = []
    results.append(test_memory_system(config))
    results.append(test_task_result())
    results.append(test_voice_engine(config))
    results.append(test_execution_kernel(config))
    results.append(test_llm_router(config))
    
    print("\n" + "=" * 50)
    passed = sum(1 for r in results if r)
    print(f"Tests Passed: {passed}/{len(results)}")
    if all(results):
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED!")
        sys.exit(1)
