default:
	node find4u-convert-schema-zod2json.js | \
		PYTHONIOENCODING=utf-8 jsonschema-markdown - -t "Properties" --no-empty-columns \
		> source/dev/find4u-cli/config/config.md
	sphinx-build -M html source build