"""
Test script - verify project structure
"""
import sys
from pathlib import Path

# Add project path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test module imports"""
    print('Testing imports...')
    
    try:
        from settings_module import get_settings, Presentation, Slide
        print('OK: config module imported')
    except Exception as e:
        print(f'FAIL: config module import failed: {e}')
    
    try:
        from core import PromptBuilder, AIClient, OutlineGenerator, PPTXBuilder
        print('OK: core module imported')
    except Exception as e:
        print(f'FAIL: core module import failed: {e}')
    
    try:
        from ui.main_window import MainWindow
        print('OK: ui module imported')
    except Exception as e:
        print(f'FAIL: ui module import failed: {e}')
    
    try:
        from utils import FileHelper, setup_logger
        print('OK: utils module imported')
    except Exception as e:
        print(f'FAIL: utils module import failed: {e}')

def test_settings():
    """Test settings management"""
    print('\nTesting settings...')
    try:
        from settings_module import get_settings
        settings = get_settings()
        config = settings.get_ai_config()
        print(f'OK: AI config - provider={config.get("provider", "N/A")}, model={config.get("model", "N/A")}')
        
        ppt_config = settings.get_ppt_config()
        print(f'OK: PPT config - theme={ppt_config.get("theme", "N/A")}, language={ppt_config.get("language", "N/A")}')
    except Exception as e:
        print(f'FAIL: settings test failed: {e}')

def test_pptx_builder():
    """Test PPTX building"""
    print('\nTesting PPTX builder...')
    try:
        from settings_module import Presentation, Slide
        from core.pptx_builder import PPTXBuilder
        
        # Create test presentation
        presentation = Presentation(
            title='Test Presentation',
            theme='business',
            language='zh'
        )
        
        # Add test slides
        slides_data = [
            {'title': 'Cover', 'points': [], 'notes': 'This is the cover page'},
            {'title': 'Table of Contents', 'points': ['Chapter 1 Overview', 'Chapter 2 Content', 'Chapter 3 Summary'], 'notes': 'Content overview'},
            {'title': 'Chapter 1', 'points': ['Point 1', 'Point 2', 'Point 3'], 'notes': 'Detailed explanation'},
        ]
        
        for i, data in enumerate(slides_data, 1):
            slide = Slide(
                page=i,
                title=data['title'],
                points=data['points'],
                notes=data['notes'],
            )
            presentation.add_slide(slide)
        
        # Build PPTX
        builder = PPTXBuilder()
        output_path = Path(__file__).parent / 'test_output' / 'test.pptx'
        output_path.parent.mkdir(exist_ok=True)
        
        result_path = builder.build(presentation, str(output_path))
        print(f'OK: PPTX built successfully: {result_path}')
        
        # Generate HTML preview
        html_content = builder.preview_html(presentation)
        html_path = Path(__file__).parent / 'test_output' / 'preview.html'
        html_path.write_text(html_content, encoding='utf-8')
        print(f'OK: HTML preview generated: {html_path}')
        
    except Exception as e:
        print(f'FAIL: PPTX builder test failed: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print('=' * 50)
    print('AutoSlide Project Test')
    print('=' * 50)
    
    test_imports()
    test_settings()
    test_pptx_builder()
    
    print('\n' + '=' * 50)
    print('Test completed!')
    print('=' * 50)
