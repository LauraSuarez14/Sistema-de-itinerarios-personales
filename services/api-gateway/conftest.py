"""Presencia de este archivo en la raíz de services/api-gateway asegura que
pytest agregue este directorio a sys.path (modo de import "prepend"), para
que `import app` funcione sin importar desde qué directorio se invoque
`pytest` ni si el paquete está instalado."""
