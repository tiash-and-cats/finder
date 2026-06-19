default:
	node find4u-cli-convert-config-zod2json.js | \
		PYTHONIOENCODING=utf-8 jsonschema-markdown - -t "Properties" --no-empty-columns \
		> source/dev/find4u-cli/config/config.md
	node find4u-cli-get-usage.js > source/dev/find4u-cli/usage.md
	sphinx-build -M html source build