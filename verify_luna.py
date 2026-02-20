import os
import sys
import json
import time
from unittest.mock import MagicMock, patch

# Mock DISPLAY environment variable for headless testing of pyautogui/mouseinfo
if 'DISPLAY' not in os.environ:
    os.environ['DISPLAY'] = ':99.0' # A dummy display

# Apply mocks for GUI-related modules before importing LUNA AI Agent modules
with patch.dict(sys.modules, {
    'pyautogui': MagicMock(),
    'mouseinfo': MagicMock(),
    'pynput': MagicMock(),
    'psutil': MagicMock()
}):
    # Add the project root to the Python path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

    from core.loop import CognitiveLoop
    from llm.router import LLMRouter
    from memory.system import MemorySystem
    from execution.kernel import ExecutionKernel
    from voice.engine import VoiceEngine

    # Mock LLMManager and its provider for testing without actual API calls
    class MockLLMProvider:
        def chat_completion(self, messages):
            # Simulate LLM response based on prompt content
            last_message = messages[-1]["content"]
            if "plan to achieve" in last_message:
                # Simulate planning response
                return {"content": json.dumps({
                    "action": "plan",
                    "plan": [
                        {"step": 1, "description": "Identify current directory", "tool": "shell", "command": "pwd"},
                        {"step": 2, "description": "List files in current directory", "tool": "shell", "command": "ls -la"},
                        {"step": 3, "description": "Summarize findings", "tool": "reflection", "thought": "Summarize the output of the previous steps."}
                    ]
                })}
            elif "Summarize the following conversation" in last_message:
                return {"content": "Summarized conversation for testing."} # Simulate summarization
            elif "Summarize the following list of past completed tasks" in last_message:
                return {"content": "Summarized episodic memory for testing."} # Simulate episodic summarization
            else:
                # Simulate conversational response
                return {"content": "Hello! How can I help you today?"}

        def extract_json(self, text):
            try:
                # Attempt to find and parse JSON within the text
                start = text.find("{")
                end = text.rfind("}")
                if start != -1 and end != -1:
                    json_str = text[start : end + 1]
                    return json.loads(json_str)
            except json.JSONDecodeError:
                pass
            return None

    class MockLLMManager:
        def get_provider(self):
            return MockLLMProvider()

    # Mock the config for testing
    TEST_CONFIG = {
        "llm": {
            "default_provider": "mock",
            "providers": {
                "mock": {"api_key": "test_key", "model": "mock_model"}
            }
        },
        "memory": {
            "max_tokens": 1000,
            "compression_threshold": 0.75
        },
        "voice": {
            "wake_word_enabled": False,
            "passive_listening_enabled": False,
            "acknowledgment_phrases": ["Hmm?", "Yes?"]
        }
    }

    # --- Test Functions ---

    def test_llm_router():
        print("\n--- Testing LLM Router ---")
        mock_llm_manager = MockLLMManager()
        router = LLMRouter(TEST_CONFIG, llm_manager=mock_llm_manager)
        # Patch the LLM call to return specific responses for routing
        with patch.object(mock_llm_manager, 'get_provider') as mock_get_provider:
            mock_get_provider.return_value.chat_completion.side_effect = [
                {"content": json.dumps({"classification": "conversation", "response": "Hello there!"})},
                {"content": json.dumps({"classification": "action", "action": {"tool": "shell", "command": "ls"}})}
            ]

            # Test conversational input
            classification, response = router.classify_input("Hi LUNA, how are you?")
            print(f"Input: 'Hi LUNA, how are you?' -> Classification: {classification}, Response: {response}")
            assert classification == "conversation"
            assert response == "Hello there!"

            # Test action input
            classification, response = router.classify_input("LUNA, list files in current directory.")
            print(f"Input: 'LUNA, list files in current directory.' -> Classification: {classification}, Response: {response}")
            assert classification == "action"
            assert response["action"]["tool"] == "shell"
        print("LLM Router tests passed.")

    def test_memory_system():
        print("\n--- Testing Memory System ---")
        memory = MemorySystem(TEST_CONFIG)
        memory.set_goal("Test memory functionality")

        # Test add_short_term and token counting
        memory.add_short_term("user", "This is a test message for short term memory.")
        memory.add_short_term("agent", "Acknowledged. Testing token count.")
        print(f"Short-term memory token count: {memory.get_token_count()}")
        assert memory.get_token_count() > 0

        # Test duplicate message guard
        initial_len = len(memory.short_term)
        memory.add_short_term("agent", "Acknowledged. Testing token count.")
        assert len(memory.short_term) == initial_len # Should not add duplicate
        print("Duplicate message guard working.")

        # Test compression (mocking LLM summarization)
        with patch.object(memory.llm_manager, 'get_provider') as mock_get_provider:
            mock_get_provider.return_value.chat_completion.return_value = {"content": "Summarized context."}
            # Manually add enough content to trigger compression threshold
            for _ in range(50):
                memory.add_short_term("user", "a very long message to trigger compression. ")
            print(f"Short-term memory token count before compression: {memory.get_token_count()}")
            assert memory.needs_compression()
            memory._manage_token_pressure() # Manually trigger
            print(f"Short-term memory token count after compression: {memory.get_token_count()}")
            assert len(memory.short_term) < 55 # Should be compressed
            assert "Summarized context." in memory.short_term[0]["content"]
        print("Memory compression and token counting tests passed.")

        # Test clear_short_term
        memory.clear_short_term()
        assert not memory.short_term
        assert not memory.execution_state # Should also be cleared
        print("clear_short_term also clears execution_state.")

    def test_cognitive_loop():
        print("\n--- Testing Cognitive Loop ---")
        # Mock dependencies for CognitiveLoop
        mock_config = TEST_CONFIG
        mock_memory = MemorySystem(mock_config)
        mock_kernel = ExecutionKernel(mock_config)
        mock_router = LLMRouter(mock_config)

        # Patch LLM calls within the loop for predictable behavior
        with (
            patch.object(mock_router.llm_manager, 'get_provider') as mock_router_provider,
            patch.object(mock_memory.llm_manager, 'get_provider') as mock_memory_provider,
            patch.object(mock_kernel, '_execute_shell_command') as mock_shell_command
        ):
            # Mock router to always classify as 'plan' for this test
            mock_router_provider.return_value.chat_completion.return_value = {"content": json.dumps({
                "classification": "action",
                "action": {"tool": "plan", "thought": "Need to plan for the goal."}
            })}
            mock_router_provider.return_value.extract_json.return_value = {
                "classification": "action",
                "action": {"tool": "plan", "thought": "Need to plan for the goal."}
            }

            # Mock planning LLM response
            mock_memory_provider.return_value.chat_completion.side_effect = [
                # First call for planning
                {"content": json.dumps({
                    "action": "plan",
                    "plan": [
                        {"step": 1, "description": "Identify current directory", "tool": "shell", "command": "pwd"},
                        {"step": 2, "description": "List files", "tool": "shell", "command": "ls"}
                    ]
                })},
                # Second call for reflection
                {"content": json.dumps({
                    "action": "reflection",
                    "outcome": "success",
                    "thought": "Successfully identified and listed files."
                })}
            ]
            mock_memory_provider.return_value.extract_json.side_effect = [
                # First call for planning
                {
                    "action": "plan",
                    "plan": [
                        {"step": 1, "description": "Identify current directory", "tool": "shell", "command": "pwd"},
                        {"step": 2, "description": "List files", "tool": "shell", "command": "ls"}
                    ]
                },
                # Second call for reflection
                {
                    "action": "reflection",
                    "outcome": "success",
                    "thought": "Successfully identified and listed files."
                }
            ]

            # Mock shell command execution
            mock_shell_command.side_effect = [
                {"status": "success", "content": "/home/ubuntu", "verified": True},
                {"status": "success", "content": "file1.txt\nfile2.txt", "verified": True}
            ]

            loop = CognitiveLoop(mock_config, mock_memory, mock_kernel, mock_router)
            loop.set_goal("Find and list files")
            result = loop.run("Find and list files in the current directory.")

            print(f"Cognitive Loop final result: {result}")
            assert result["status"] == "success"
            assert "Successfully identified and listed files." in result["content"]
            assert mock_shell_command.call_count == 2
        print("Cognitive Loop tests passed.")

    def test_voice_engine():
        print("\n--- Testing Voice Engine ---")
        # Test with wake_word_enabled = False (default for this test)
        voice_engine = VoiceEngine(TEST_CONFIG)
        assert not voice_engine.wake_word_enabled
        assert not voice_engine.passive_listening_enabled
        assert voice_engine.acknowledgment_phrases == ["Hmm?", "Yes?"]

        # Test graceful degradation (mocking imports)
        with patch.dict(sys.modules, {
            'vosk': None, 'sounddevice': None, 'pyaudio': None, 'speech_recognition': None
        }):
            # Re-initialize to simulate missing dependencies
            voice_engine_no_deps = VoiceEngine(TEST_CONFIG)
            assert not voice_engine_no_deps.voice_mode_enabled
            print("Voice engine gracefully degrades without dependencies.")

        print("Voice Engine tests passed.")

    def test_execution_kernel():
        print("\n--- Testing Execution Kernel ---")
        kernel = ExecutionKernel(TEST_CONFIG)

        # Mock subprocess.run for shell commands
        with patch('subprocess.run') as mock_subprocess_run:
            mock_subprocess_run.return_value = MagicMock(stdout=b'hello\n', stderr=b'', returncode=0)
            result = kernel._execute_shell_command("echo hello")
            print(f"Shell command result: {result}")
            assert result["status"] == "success"
            assert result["content"] == "hello\n"

            mock_subprocess_run.return_value = MagicMock(stdout=b'', stderr=b'error\n', returncode=1)
            result = kernel._execute_shell_command("bad_command")
            print(f"Bad command result: {result}")
            assert result["status"] == "failed"
            assert "error\n" in result["error"]

        # Mock psutil for _launch_app and _process_operation
        with patch('psutil.process_iter') as mock_process_iter:
            with patch('subprocess.Popen') as mock_popen:
                with patch('time.sleep'):

                    # Test _launch_app success
                    mock_popen.return_value = MagicMock(pid=1234)
                    mock_process_iter.return_value = [MagicMock(info={'name': 'testapp', 'pid': 1234})]
                    result = kernel._launch_app("testapp")
                    print(f"Launch app result: {result}")
                    assert result["status"] == "success"
                    assert result["verified"]

                    # Test _launch_app failure (process not found)
                    mock_process_iter.return_value = []
                    result = kernel._launch_app("nonexistent_app")
                    print(f"Launch nonexistent app result: {result}")
                    assert result["status"] == "failed"
                    assert not result["verified"]

                    # Test _process_operation kill success
                    mock_proc = MagicMock(pid=5678)
                    mock_proc.is_running.side_effect = [True, False] # Running then not running
                    mock_process_iter.return_value = [mock_proc]
                    result = kernel._process_operation("kill", "5678")
                    print(f"Kill process result: {result}")
                    assert result["status"] == "success"
                    assert result["verified"]

        print("Execution Kernel tests passed.")


if __name__ == "__main__":
    print("Starting LUNA AI Agent v4.0 Verification Tests...")
    test_llm_router()
    test_memory_system()
    test_cognitive_loop()
    test_voice_engine()
    test_execution_kernel()
    print("\nAll LUNA AI Agent v4.0 verification tests completed.")
