# interface/base_interface.py
from abc import ABC, abstractmethod


class BaseInterface(ABC):
    """Contrato que toda UI debe implementar.
    El Core Engine solo conoce esta clase, nunca CLI ni GUI directamente."""

    @abstractmethod
    def run(self) -> None:
        """Punto de entrada principal de la interfaz."""
        pass

    @abstractmethod
    def display_message(self, message: str) -> None:
        """Muestra un mensaje al usuario."""
        pass

    @abstractmethod
    def get_input(self, prompt: str) -> str:
        """Solicita input al usuario y retorna el texto."""
        pass

    @abstractmethod
    def display_menu(self, title: str, options: dict) -> str:
        """Muestra un menú y retorna la opción elegida."""
        pass