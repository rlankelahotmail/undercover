from backend.main import app


def operations():
    for path, methods in app.openapi()["paths"].items():
        for method, operation in methods.items():
            yield f"{method.upper()} {path}", operation


def test_every_operation_has_an_id_and_a_one_line_docstring():
    for name, operation in operations():
        assert operation.get("operationId"), name
        assert len(operation["description"].strip().splitlines()) == 1, name


def test_no_operation_has_optional_inputs():
    schemas = app.openapi()["components"]["schemas"]
    for name, operation in operations():
        for parameter in operation.get("parameters", []):
            assert parameter["required"], name
        if "requestBody" in operation:
            reference = operation["requestBody"]["content"]["application/json"][
                "schema"
            ]
            body = schemas[reference["$ref"].split("/")[-1]]
            assert set(body["required"]) == set(body["properties"]), name
