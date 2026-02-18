"""
Tools for Hello World skill

These tools can be invoked by the Cell 0 OS engine.
"""

# Greetings in different languages
GREETINGS = {
    "en": "Hello",
    "es": "¡Hola",
    "fr": "Bonjour",
    "de": "Hallo",
    "it": "Ciao",
    "jp": "こんにちは",
    "zh": "你好",
}

FAREWELLS = {
    "en": "Goodbye",
    "es": "Adiós",
    "fr": "Au revoir",
    "de": "Auf Wiedersehen",
    "it": "Arrivederci",
    "jp": "さようなら",
    "zh": "再见",
}


def say_hello(name: str = "World", language: str = "en", **kwargs) -> dict:
    """
    Returns a greeting message.
    
    Args:
        name: Name to greet
        language: Language code (en, es, fr, etc.)
        **kwargs: Additional parameters passed by the engine
        
    Returns:
        Dictionary with greeting message and metadata
    """
    greeting = GREETINGS.get(language, GREETINGS["en"])
    message = f"{greeting}, {name}!"
    
    return {
        "message": message,
        "greeting": greeting,
        "name": name,
        "language": language,
        "skill": "hello_world"
    }


def say_goodbye(name: str = "Friend", language: str = "en", **kwargs) -> dict:
    """
    Returns a farewell message.
    
    Args:
        name: Name to bid farewell
        language: Language code
        **kwargs: Additional parameters passed by the engine
        
    Returns:
        Dictionary with farewell message and metadata
    """
    farewell = FAREWELLS.get(language, FAREWELLS["en"])
    message = f"{farewell}, {name}!"
    
    return {
        "message": message,
        "farewell": farewell,
        "name": name,
        "language": language,
        "skill": "hello_world"
    }


def get_supported_languages(**kwargs) -> dict:
    """
    Returns the list of supported languages.
    
    Returns:
        Dictionary with supported languages
    """
    return {
        "greetings": list(GREETINGS.keys()),
        "farewells": list(FAREWELLS.keys())
    }
