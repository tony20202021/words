
critical_libraries = [
    "huggingface_hub",
    "transformers",
    "diffusers",
    "accelerate",
    "safetensors",
    "xformers",
]

for lib_name in critical_libraries:
    try:
        print(f"{lib_name}")
        lib = __import__(lib_name)
        print(f"\t imported")
        version = getattr(lib, "__version__", "unknown")
        print(f"\t {version}")
    except ImportError as e:
        print(f"\t not found")
        print(e)
