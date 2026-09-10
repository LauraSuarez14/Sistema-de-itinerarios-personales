"""Paquete destino de los stubs gRPC generados en tiempo de build
(Dockerfile) a partir de `proto/airport.proto`.

Este directorio se mantiene vacio en el repositorio a proposito (ver
`.gitignore`: `app/infrastructure/grpc_client/*_pb2.py` y `*_pb2_grpc.py`
estan ignorados). Al construir la imagen Docker, `python -m grpc_tools.protoc`
genera aqui `airport_pb2.py` y `airport_pb2_grpc.py`. No se deben commitear
esos archivos generados ni escribirse a mano.
"""
