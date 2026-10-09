trash dist
uv build
export UV_PUBLISH_TOKEN=$(grep -E '^PYPI_TOKEN=' .env | cut -d= -f2-)
uv publish
