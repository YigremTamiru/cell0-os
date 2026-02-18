"""
CLI commands for Hello World skill

These commands are accessible via `cell0ctl hello` and `cell0ctl goodbye`.
"""

import argparse

from .tools import say_hello, say_goodbye, get_supported_languages


def hello_command(args: argparse.Namespace = None) -> int:
    """
    CLI command to print a hello message.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success)
    """
    # Parse arguments if provided as list
    if args is None or not hasattr(args, 'name'):
        parser = argparse.ArgumentParser(description='Say hello')
        parser.add_argument('--name', '-n', default='World', help='Name to greet')
        parser.add_argument('--language', '-l', default='en', help='Language code')
        parsed_args = parser.parse_args(args if isinstance(args, list) else None)
    else:
        parsed_args = args
    
    # Get greeting
    result = say_hello(
        name=getattr(parsed_args, 'name', 'World'),
        language=getattr(parsed_args, 'language', 'en')
    )
    
    print(result['message'])
    return 0


def goodbye_command(args: argparse.Namespace = None) -> int:
    """
    CLI command to print a goodbye message.
    
    Args:
        args: Command line arguments
        
    Returns:
        Exit code (0 for success)
    """
    # Parse arguments if provided as list
    if args is None or not hasattr(args, 'name'):
        parser = argparse.ArgumentParser(description='Say goodbye')
        parser.add_argument('--name', '-n', default='Friend', help='Name to bid farewell')
        parser.add_argument('--language', '-l', default='en', help='Language code')
        parsed_args = parser.parse_args(args if isinstance(args, list) else None)
    else:
        parsed_args = args
    
    # Get farewell
    result = say_goodbye(
        name=getattr(parsed_args, 'name', 'Friend'),
        language=getattr(parsed_args, 'language', 'en')
    )
    
    print(result['message'])
    return 0


def list_languages_command(args: argparse.Namespace = None) -> int:
    """
    CLI command to list supported languages.
    
    Returns:
        Exit code (0 for success)
    """
    result = get_supported_languages()
    
    print("Supported languages for greetings:")
    for lang in result['greetings']:
        print(f"  - {lang}")
    
    print("\nSupported languages for farewells:")
    for lang in result['farewells']:
        print(f"  - {lang}")
    
    return 0
