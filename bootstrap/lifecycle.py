"""Application lifecycle (E2.T1).

Owns startup and shutdown of the composition root. There are no module-level
side effects: a container is only built when ``create_container`` / ``lifespan``
is called, and ``shutdown`` releases resources deterministically.
"""

from contextlib import contextmanager
from typing import Iterator, Optional

from bootstrap.container import Container
from bootstrap.settings.loaders import load_settings


def create_container(environment=None,
                     env_file_path: Optional[str] = None,
                     base_data_dir: Optional[str] = None) -> Container:
    """Build a fully-configured container for ``environment``."""
    settings = load_settings(environment, env_file_path)
    container = Container(settings, base_data_dir=base_data_dir)
    
    # Bridge to the active container for backward compatibility
    import bootstrap.container
    bootstrap.container.container = container
    try:
        from application.containers.container import container as legacy_container
        legacy_container.register("risk_engine", container.resolve("risk_engine"))
    except Exception:
        pass
        
    return container


@contextmanager
def lifespan(environment=None,
             env_file_path: Optional[str] = None,
             base_data_dir: Optional[str] = None) -> Iterator[Container]:
    """Context manager that builds the container and tears it down on exit."""
    container = create_container(environment, env_file_path, base_data_dir)
    try:
        yield container
    finally:
        container.shutdown()
