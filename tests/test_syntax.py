import py_compile
import pytest
from pathlib import Path

def test_python_syntax():
    """Test that all Python files have valid syntax."""
    src_dir = Path(__file__).parent.parent / "src"
    python_files = list(src_dir.rglob("*.py"))
    
    assert len(python_files) > 0, "No Python files found to test"
    
    errors = []
    for py_file in python_files:
        try:
            py_compile.compile(str(py_file), doraise=True)
        except py_compile.PyCompileError as e:
            errors.append(f"{py_file.relative_to(src_dir)}: {e}")
    
    if errors:
        pytest.fail(f"Syntax errors found in {len(errors)} file(s):\n" + "\n".join(errors))
