from typing import Dict, Any
from application.configs.environments import Environment, get_current_environment
import importlib


class ProfileLoader:
    """
    Responsible for loading configuration profiles based on the current environment.
    """
    
    @staticmethod
    def load_profile(env: Environment = None) -> Dict[str, Any]:
        """
        Load the configuration profile for the specified environment.
        
        Args:
            env: Environment to load profile for. If None, uses current environment.
            
        Returns:
            Dictionary containing the configuration profile
            
        Raises:
            ImportError: If the profile module cannot be loaded
            AttributeError: If the profile module doesn't have CONFIG dictionary
        """
        if env is None:
            env = get_current_environment()
        
        # Import the appropriate profile module based on environment
        try:
            module_path = f"application.configs.profiles.{env.value}"
            profile_module = importlib.import_module(module_path)
        except ImportError as e:
            raise ImportError(f"Could not load profile for environment '{env.value}': {str(e)}")
        
        # Extract the CONFIG dictionary from the module
        if not hasattr(profile_module, 'CONFIG'):
            raise AttributeError(f"Profile module '{module_path}' does not have CONFIG attribute")
        
        config_dict = getattr(profile_module, 'CONFIG')
        if not isinstance(config_dict, dict):
            raise TypeError(f"CONFIG in profile module '{module_path}' is not a dictionary")
        
        return config_dict
    
    @staticmethod
    def get_available_profiles() -> Dict[Environment, bool]:
        """
        Check which profiles are available by attempting to import them.
        
        Returns:
            Dictionary mapping environments to availability status
        """
        available_profiles = {}
        
        for env in Environment:
            try:
                module_path = f"application.configs.profiles.{env.value}"
                importlib.import_module(module_path)
                available_profiles[env] = True
            except ImportError:
                available_profiles[env] = False
        
        return available_profiles