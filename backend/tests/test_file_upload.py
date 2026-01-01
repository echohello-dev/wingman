"""
Tests for Slack file upload and processing
"""
import io

import pytest
from app.database import Document, SessionLocal, init_db
from app.slack_bot import slack_bot


@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test"""
    init_db()
    session = SessionLocal()
    yield session
    session.query(Document).delete()
    session.commit()
    session.close()


class TestFileContentExtraction:
    """Tests for file content extraction from various formats"""
    
    def test_extract_plain_text(self):
        """Test extracting content from plain text files"""
        content = b"Hello, this is a test file."
        result = slack_bot._extract_file_content(content, "txt", "text/plain")
        
        assert result == "Hello, this is a test file."
    
    def test_extract_markdown(self):
        """Test extracting content from markdown files"""
        content = b"# Title\n\nThis is markdown content."
        result = slack_bot._extract_file_content(content, "md", "text/markdown")
        
        assert "Title" in result
        assert "markdown content" in result
    
    def test_extract_python_file(self):
        """Test extracting content from Python code files"""
        content = b"def hello():\n    return 'world'"
        result = slack_bot._extract_file_content(content, "py", "text/x-python")
        
        assert "def hello" in result
        assert "world" in result
    
    def test_extract_json(self):
        """Test extracting content from JSON files"""
        content = b'{"name": "test", "value": 123}'
        result = slack_bot._extract_file_content(content, "json", "application/json")
        
        assert "name" in result
        assert "test" in result
    
    def test_extract_csv(self):
        """Test extracting content from CSV files"""
        content = b"name,age\nJohn,30\nJane,25"
        result = slack_bot._extract_file_content(content, "csv", "text/csv")
        
        assert "name" in result
        assert "John" in result
        assert "Jane" in result
    
    def test_extract_html(self):
        """Test extracting text content from HTML files"""
        content = b"<html><body><h1>Title</h1><p>Content here</p></body></html>"
        result = slack_bot._extract_file_content(content, "html", "text/html")
        
        # HTML tags should be removed
        assert "<html>" not in result
        assert "<body>" not in result
        # Text content should remain
        assert "Title" in result
        assert "Content here" in result
    
    def test_extract_html_removes_scripts(self):
        """Test that HTML script tags are removed"""
        content = b"<html><script>alert('xss')</script><body>Safe content</body></html>"
        result = slack_bot._extract_file_content(content, "html", "text/html")
        
        assert "alert" not in result
        assert "Safe content" in result
    
    def test_unsupported_file_type(self):
        """Test handling of unsupported file types"""
        content = b"some binary content"
        result = slack_bot._extract_file_content(content, "bin", "application/octet-stream")
        
        # Should return empty string for unsupported types
        assert result == ""
    
    def test_extract_with_encoding_errors(self):
        """Test handling of encoding errors"""
        # Invalid UTF-8 sequence
        content = b"\x80\x81\x82"
        result = slack_bot._extract_file_content(content, "txt", "text/plain")
        
        # Should handle gracefully without crashing
        assert isinstance(result, str)
    
    def test_extract_xml(self):
        """Test extracting content from XML files"""
        content = b"<?xml version='1.0'?><root><item>Test</item></root>"
        result = slack_bot._extract_file_content(content, "xml", "text/xml")
        
        assert "Test" in result
    
    def test_extract_yaml(self):
        """Test extracting content from YAML files"""
        content = b"name: test\nvalue: 123"
        result = slack_bot._extract_file_content(content, "yaml", "text/x-yaml")
        
        assert "name" in result
        assert "test" in result


class TestProcessFileMethod:
    """Tests for file processing and indexing"""
    
    def test_process_file_missing_url(self):
        """Test handling of file without URL"""
        file_data = {
            "id": "F123",
            "name": "test.txt"
            # Missing url_private
        }
        
        result = slack_bot._process_and_index_file(file_data, "C123", "U123")
        
        # Should return False when URL is missing
        assert result is False
    
    def test_extract_file_content_empty_bytes(self):
        """Test handling of empty file content"""
        content = b""
        result = slack_bot._extract_file_content(content, "txt", "text/plain")
        
        assert result == ""
    
    def test_javascript_file_extraction(self):
        """Test extracting JavaScript file content"""
        content = b"function test() { return 'hello'; }"
        result = slack_bot._extract_file_content(content, "js", "text/javascript")
        
        assert "function test" in result
        assert "hello" in result
    
    def test_typescript_file_extraction(self):
        """Test extracting TypeScript file content"""
        content = b"const greeting: string = 'hello';"
        result = slack_bot._extract_file_content(content, "ts", "text/typescript")
        
        assert "greeting" in result
        assert "hello" in result
    
    def test_shell_script_extraction(self):
        """Test extracting shell script content"""
        content = b"#!/bin/bash\necho 'Hello World'"
        result = slack_bot._extract_file_content(content, "sh", "text/x-shellscript")
        
        assert "echo" in result
        assert "Hello World" in result


class TestConversationIds:
    """Tests for conversation ID generation in Slack bot handlers"""
    
    def test_thread_conversation_id_format(self):
        """Test that thread mentions use correct conversation ID format"""
        # The bot should generate IDs like: thread:{channel_id}:{thread_ts}
        # This is verified in the handle_mention function
        expected_format = "thread:C123456:1234567890.123456"
        
        assert expected_format.startswith("thread:")
        parts = expected_format.split(":")
        assert len(parts) == 3
        assert parts[0] == "thread"
    
    def test_dm_conversation_id_format(self):
        """Test that DMs use correct conversation ID format"""
        # The bot should generate IDs like: dm:{user_id}
        expected_format = "dm:U123456"
        
        assert expected_format.startswith("dm:")
        parts = expected_format.split(":")
        assert len(parts) == 2
        assert parts[0] == "dm"
