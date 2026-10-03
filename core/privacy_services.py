"""
Permissões de que os testes precisam.

Módulo neutro para que ``core`` e ``tests.support`` compartilhem os
mesmos identificadores sem criar dependência entre as camadas. No
Android são intenção declarada pelas fixtures: quem concede é o
autoGrantPermissions na instalação do app.
"""

# === Permissões utilizadas pela suíte ===
CAMERA = "camera"
LOCATION = "location"
MICROPHONE = "microphone"
PHOTOS = "photos"
