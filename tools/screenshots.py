"""Screenshot tool for capturing screen and code"""
import os
import sys
import re
from PIL import Image, ImageDraw, ImageFont
from langchain_core.tools import tool

@tool
def take_screenshot(output_path: str = "screenshot.png") -> str:
    """
    Take a screenshot of the current screen.
    
    Args:
        output_path: Path where screenshot will be saved
    
    Returns:
        Success message with file path
    """
    try:
        import pyautogui
        pyautogui.FAILSAFE = False
        img = pyautogui.screenshot()
        img.save(output_path)
        abs_path = os.path.abspath(output_path)
        
        if os.path.exists(abs_path):
            file_size = os.path.getsize(abs_path)
            return f"Screenshot saved to: {abs_path} (Size: {file_size} bytes)"
        else:
            return f"Screenshot failed: File was not created at {abs_path}"
            
    except ImportError:
        return "PyAutoGUI not installed. Install with: pip install pyautogui"
    except Exception as e:
        return f"Screenshot failed: {str(e)}"

@tool
def screenshot_code_file(file_path: str, output_path: str = "code_screenshot.png") -> str:
    """
    Create a screenshot-like image of an entire code file with syntax highlighting.
    
    Args:
        file_path: Path to the code file
        output_path: Path where screenshot will be saved
    
    Returns:
        Success message with file path
    """
    try:
        if not os.path.exists(file_path):
            return f"File not found: {file_path}"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        return _create_code_image(code, output_path, f"File: {file_path}")
    
    except Exception as e:
        return f"Code screenshot failed: {str(e)}"

@tool
def screenshot_code_function(file_path: str, function_name: str, output_path: str = "function_screenshot.png") -> str:
    """
    Create a screenshot of a specific function from a code file.
    
    Args:
        file_path: Path to the code file
        function_name: Name of the function to capture
        output_path: Path where screenshot will be saved
    
    Returns:
        Success message with file path
    """
    try:
        if not os.path.exists(file_path):
            return f"File not found: {file_path}"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Find function
        func_lines = _extract_function(lines, function_name)
        if not func_lines:
            return f"Function '{function_name}' not found in {file_path}"
        
        code = ''.join(func_lines)
        return _create_code_image(code, output_path, f"Function: {function_name}")
    
    except Exception as e:
        return f"Function screenshot failed: {str(e)}"

@tool
def screenshot_code_class(file_path: str, class_name: str, output_path: str = "class_screenshot.png") -> str:
    """
    Create a screenshot of a specific class from a code file.
    
    Args:
        file_path: Path to the code file
        class_name: Name of the class to capture
        output_path: Path where screenshot will be saved
    
    Returns:
        Success message with file path
    """
    try:
        if not os.path.exists(file_path):
            return f"File not found: {file_path}"
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Find class
        class_lines = _extract_class(lines, class_name)
        if not class_lines:
            return f"Class '{class_name}' not found in {file_path}"
        
        code = ''.join(class_lines)
        return _create_code_image(code, output_path, f"Class: {class_name}")
    
    except Exception as e:
        return f"Class screenshot failed: {str(e)}"

def _extract_function(lines, func_name):
    """Extract function lines from code"""
    func_lines = []
    in_function = False
    indent_level = 0
    
    for line in lines:
        if re.match(rf'^\s*def\s+{re.escape(func_name)}\s*\(', line):
            in_function = True
            indent_level = len(line) - len(line.lstrip())
            func_lines.append(line)
        elif in_function:
            current_indent = len(line) - len(line.lstrip())
            if line.strip() and current_indent <= indent_level and not line.strip().startswith('#'):
                break
            func_lines.append(line)
    
    return func_lines

def _extract_class(lines, class_name):
    """Extract class lines from code"""
    class_lines = []
    in_class = False
    indent_level = 0
    
    for line in lines:
        if re.match(rf'^\s*class\s+{re.escape(class_name)}\s*[\(:]', line):
            in_class = True
            indent_level = len(line) - len(line.lstrip())
            class_lines.append(line)
        elif in_class:
            current_indent = len(line) - len(line.lstrip())
            if line.strip() and current_indent <= indent_level and not line.strip().startswith('#'):
                break
            class_lines.append(line)
    
    return class_lines

def _create_code_image(code, output_path, title):
    """Create a colorful syntax-highlighted image from code text"""
    try:
        # Image settings
        font_size = 14
        line_height = 18
        padding = 25
        bg_color = (30, 30, 30)  # Dark background
        
        # Syntax colors (VS Code Dark+ theme)
        colors = {
            'keyword': (86, 156, 214),      # Blue
            'string': (206, 145, 120),      # Orange
            'comment': (106, 153, 85),      # Green
            'function': (220, 220, 170),    # Yellow
            'class': (78, 201, 176),        # Cyan
            'number': (181, 206, 168),      # Light green
            'default': (212, 212, 212)      # Light gray
        }
        
        # Try to load a monospace font
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", font_size)
        except:
            font = ImageFont.load_default()
        
        lines = code.split('\n')
        max_width = max(len(line) for line in lines) * 9 + padding * 2
        height = len(lines) * line_height + padding * 3 + 40
        
        # Create image with gradient background
        img = Image.new('RGB', (max_width, height), bg_color)
        draw = ImageDraw.Draw(img)
        
        # Draw title with background
        title_bg = (45, 45, 45)
        draw.rectangle([0, 0, max_width, padding + 25], fill=title_bg)
        draw.text((padding, padding), title, fill=(255, 255, 255), font=font)
        
        # Draw code with syntax highlighting
        y = padding * 2 + 30
        for i, line in enumerate(lines):
            # Line number
            line_num = str(i + 1).rjust(3)
            draw.text((5, y), line_num, fill=(100, 100, 100), font=font)
            
            # Syntax highlight the line
            x_offset = padding + 30
            tokens = _tokenize_line(line)
            
            for token, token_type in tokens:
                color = colors.get(token_type, colors['default'])
                draw.text((x_offset, y), token, fill=color, font=font)
                x_offset += len(token) * 9
            
            y += line_height
        
        img.save(output_path)
        abs_path = os.path.abspath(output_path)
        file_size = os.path.getsize(abs_path)
        return f"Colorful code screenshot saved to: {abs_path} (Size: {file_size} bytes)"
    
    except Exception as e:
        return f"Image creation failed: {str(e)}"

def _tokenize_line(line):
    """Simple tokenizer for syntax highlighting"""
    tokens = []
    i = 0
    while i < len(line):
        # Skip whitespace
        if line[i].isspace():
            start = i
            while i < len(line) and line[i].isspace():
                i += 1
            tokens.append((line[start:i], 'default'))
            continue
        
        # Comments
        if line[i:i+1] == '#':
            tokens.append((line[i:], 'comment'))
            break
        
        # Strings
        if line[i] in '"\'':
            quote = line[i]
            start = i
            i += 1
            while i < len(line) and line[i] != quote:
                if line[i] == '\\':
                    i += 2
                else:
                    i += 1
            if i < len(line):
                i += 1
            tokens.append((line[start:i], 'string'))
            continue
        
        # Numbers
        if line[i].isdigit():
            start = i
            while i < len(line) and (line[i].isdigit() or line[i] == '.'):
                i += 1
            tokens.append((line[start:i], 'number'))
            continue
        
        # Keywords and identifiers
        if line[i].isalpha() or line[i] == '_':
            start = i
            while i < len(line) and (line[i].isalnum() or line[i] == '_'):
                i += 1
            word = line[start:i]
            
            # Python keywords
            keywords = {'def', 'class', 'if', 'else', 'elif', 'for', 'while', 'try', 'except', 
                       'import', 'from', 'return', 'yield', 'async', 'await', 'with', 'as',
                       'True', 'False', 'None', 'and', 'or', 'not', 'in', 'is', 'lambda'}
            
            if word in keywords:
                if word in ['def', 'class']:
                    tokens.append((word, 'keyword'))
                    # Next word after def/class is function/class name
                    if i < len(line):
                        while i < len(line) and line[i].isspace():
                            tokens.append((line[i], 'default'))
                            i += 1
                        if i < len(line) and (line[i].isalpha() or line[i] == '_'):
                            start = i
                            while i < len(line) and (line[i].isalnum() or line[i] == '_'):
                                i += 1
                            func_name = line[start:i]
                            token_type = 'class' if word == 'class' else 'function'
                            tokens.append((func_name, token_type))
                else:
                    tokens.append((word, 'keyword'))
            else:
                tokens.append((word, 'default'))
            continue
        
        # Other characters
        tokens.append((line[i], 'default'))
        i += 1
    
    return tokens

def get_screenshot_tools():
    """Return screenshot tools"""
    return [take_screenshot, screenshot_code_file, screenshot_code_function, screenshot_code_class]


