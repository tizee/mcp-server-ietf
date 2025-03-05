from . import server, rfc_parser

def main():
    server.serve()

__all__ = ["server", "rfc_parser"]

if __name__ == "__main__":
    server.serve()

