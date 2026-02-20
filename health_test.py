import sys
import os
from typing import Dict, Any

# Add the current directory to sys.path to import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from memory.system import MemorySystem
from llm.provider import LLMManager, sanitize_llm_output
# from core.loop import CognitiveLoop
import yaml

def test_memory_system():
    print("Testing MemorySystem attribute wrappers...")
    config = {"memory": {"max_tokens": 4000, "compression_threshold": 0.75}, "llm": {"default_provider": "deepseek", "providers": {"deepseek": {"api_key": "test", "model": "test", "base_url": "test"}}}}
    memory = MemorySystem(config)
    
    # Test short_term property
    assert hasattr(memory, 'short_term'), "MemorySystem missing 'short_term' property"
    assert isinstance(memory.short_term, list), "'short_term' should be a list"
    
    # Test episodic property
    assert hasattr(memory, 'episodic'), "MemorySystem missing 'episodic' property"
    assert isinstance(memory.episodic, list), "'episodic' should be a list"
    
    # Test long_term property
    assert hasattr(memory, 'long_term'), "MemorySystem missing 'long_term' property"
    assert isinstance(memory.long_term, str), "'long_term' should be a string"
    
    print("MemorySystem tests PASSED")

def test_sanitation_layer():
    print("Testing Sanitation Layer...")
    schema = {
        "required": ["plan", "status"],
        "optional": {"reasoning": "N/A", "confidence": 1.0}
    }
    
    # Test with extra keys
    response = {"plan": ["step1"], "status": "success", "extra_key": "should be dropped", "reasoning": "because"}
    sanitized = sanitize_llm_output(response, schema)
    
    assert "extra_key" not in sanitized, "Extra key should have been dropped"
    assert sanitized["plan"] == ["step1"]
    assert sanitized["status"] == "success"
    assert sanitized["reasoning"] == "because"
    assert sanitized["confidence"] == 1.0, "Optional key should have default value"
    
    # Test with missing required key
    try:
        sanitize_llm_output({"plan": []}, schema)
        assert False, "Should have raised ValueError for missing required key"
    except ValueError:
        pass
        
    print("Sanitation Layer tests PASSED")

if __name__ == "__main__":
    try:
        test_memory_system()
        test_sanitation_layer()
        print("\nAll health tests PASSED")
    except Exception as e:
        print(f"\nHealth tests FAILED: {e}")
        sys.exit(1)
