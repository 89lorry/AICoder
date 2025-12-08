# Project Group 3
# Peter Xie (28573670)
# Xin Tang (79554618)
# Keyan Miao (42708776)
# Keyi Feng (84254877)


"""
import sys
sys.path.insert(0, '.')

try:
    from utils.file_manager import FileManager
    print("✓ FileManager imported successfully")
    
    fm = FileManager()
    print("✓ FileManager instantiated successfully")
    
    # Test basic operations
    test_dir = "./test_fm_dir"
    fm.create_directory(test_dir)
    print(f"✓ Directory created: {test_dir}")
    
    test_file = fm.join_path(test_dir, "test.txt")
    fm.write_file(test_file, "Test content")
    print(f"✓ File written: {test_file}")
    
    content = fm.read_file(test_file)
    print(f"✓ File read: {content}")
    
    fm.delete_directory(test_dir)
    print(f"✓ Directory deleted: {test_dir}")
    
    print("\n✓ ALL FileManager tests passed!")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
