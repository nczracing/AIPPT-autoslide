"""
Install script - automatically install dependencies
"""
import subprocess
import sys
from pathlib import Path

def install_dependencies():
    """Install dependencies"""
    print('Installing dependencies...')
    
    requirements_path = Path(__file__).parent / 'requirements.txt'
    
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '-r', str(requirements_path)
        ])
        print('OK: Dependencies installed successfully')
        return True
    except subprocess.CalledProcessError as e:
        print(f'FAIL: Dependencies installation failed: {e}')
        return False

def test_installation():
    """Test installation"""
    print('\nTesting installation...')
    
    try:
        import PyQt6
        print(f'OK: PyQt6 version: {PyQt6.__version__}')
    except ImportError:
        print('FAIL: PyQt6 not installed')
    
    try:
        import pptx
        print(f'OK: python-pptx version: {pptx.__version__}')
    except ImportError:
        print('FAIL: python-pptx not installed')
    
    try:
        import openai
        print(f'OK: openai version: {openai.__version__}')
    except ImportError:
        print('FAIL: openai not installed')

if __name__ == '__main__':
    if install_dependencies():
        test_installation()
        print('\nInstallation complete! Run python main.py to start the application')
    else:
        print('\nInstallation failed, please check network connection and retry')
