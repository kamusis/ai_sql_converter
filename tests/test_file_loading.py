import os
import pytest
from sql_converter import SQLConverter

@pytest.fixture
def setup_test_files(tmp_path):
    """Create temporary SQL files for testing"""
    # Create test files
    file1 = tmp_path / "test1.sql"
    file2 = tmp_path / "test2.sql"
    file3 = tmp_path / "subdir" / "test3.sql"
    
    # Create subdirectory
    os.makedirs(file3.parent, exist_ok=True)
    
    # Write content to files
    file1.write_text("SELECT * FROM table1;")
    file2.write_text("SELECT * FROM table2;")
    file3.write_text("SELECT * FROM table3;")
    
    return tmp_path

def test_single_file_loading(setup_test_files):
    """Test loading a single SQL file"""
    file_path = os.path.join(setup_test_files, "test1.sql")
    files = SQLConverter.load_sql_files(file_path)
    
    assert len(files) == 1
    assert files[0][1] == "SELECT * FROM table1;"

def test_multiple_files_loading(setup_test_files):
    """Test loading multiple SQL files using semicolon separator"""
    file_path = f"{setup_test_files}/test1.sql;{setup_test_files}/test2.sql"
    files = SQLConverter.load_sql_files(file_path)
    
    assert len(files) == 2
    assert any("table1" in content for _, content in files)
    assert any("table2" in content for _, content in files)

def test_wildcard_pattern_loading(setup_test_files):
    """Test loading SQL files using wildcard pattern"""
    file_path = f"{setup_test_files}/*.sql"
    files = SQLConverter.load_sql_files(file_path)
    
    assert len(files) == 2  # Should find test1.sql and test2.sql
    assert any("table1" in content for _, content in files)
    assert any("table2" in content for _, content in files)

def test_directory_loading(setup_test_files):
    """Test loading all SQL files from a directory recursively"""
    files = SQLConverter.load_sql_files(str(setup_test_files))
    
    assert len(files) == 3  # Should find all three SQL files
    assert any("table1" in content for _, content in files)
    assert any("table2" in content for _, content in files)
    assert any("table3" in content for _, content in files)

def test_multiple_patterns_loading(setup_test_files):
    """Test loading files using multiple patterns"""
    file_path = f"{setup_test_files}/test1.sql;{setup_test_files}/subdir/*.sql"
    files = SQLConverter.load_sql_files(file_path)
    
    assert len(files) == 2
    assert any("table1" in content for _, content in files)
    assert any("table3" in content for _, content in files)

def test_nonexistent_file_error():
    """Test error handling for nonexistent files"""
    with pytest.raises(FileNotFoundError):
        SQLConverter.load_sql_files("nonexistent.sql")

def test_empty_directory_loading(tmp_path):
    """Test loading from an empty directory"""
    files = SQLConverter.load_sql_files(str(tmp_path))
    assert len(files) == 0
