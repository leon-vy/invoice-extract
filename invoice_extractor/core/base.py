from abc import ABC, abstractmethod
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class BaseProcessor(ABC):
    """Base class for all platform processors (Extraction & Validation)"""
    
    def __init__(self, platform_name: str):
        self.platform_name = platform_name
        self.logger = logging.getLogger(f"{__name__}.{platform_name}")

    @abstractmethod
    def run(self, *args, **kwargs):
        """Main entry point for the processor"""
        pass

class ProcessorRegistry:
    """Registry to manage and retrieve processors"""
    _processors = {}

    @classmethod
    def register(cls, name: str):
        """Decorator to register a processor class"""
        def wrapper(processor_class):
            cls._processors[name] = processor_class
            return processor_class
        return wrapper

    @classmethod
    def get_processor(cls, name: str) -> BaseProcessor:
        processor_class = cls._processors.get(name)
        if not processor_class:
            raise ValueError(f"No processor registered for platform: {name}")
        return processor_class()

    @classmethod
    def list_platforms(cls):
        return list(cls._processors.keys())
