import sys

if __name__ == "__main__":
    try:
        from .main import main
    except ImportError:
        print("apotheosession.main not yet implemented", file=sys.stderr)
        sys.exit(1)
    main()
