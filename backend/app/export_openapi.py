"""Print the OpenAPI spec as JSON. `make gen-client` turns it into TypeScript types."""

import json

from app.main import app

if __name__ == "__main__":
    print(json.dumps(app.openapi(), indent=2, sort_keys=True))
