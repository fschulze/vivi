from jsonschema.validators import RefResolver

import mock
import requests_mock
import yaml

import zeit.content.text.interfaces
import zeit.content.text.json
import zeit.content.text.testing


class JSONValidationTestCase(zeit.content.text.testing.FunctionalTestCase):

    schema_json = {'components': {
        'schemas': {
            'uuid': {
                'type': 'string',
                'pattern':
                    "^((\\{urn:uuid:)?([a-f0-9]{8})\\}?)$"}
        }
    }}

    def test_only_validate_if_field_in_schema(self):
        json_content = zeit.content.text.json.JSON()
        validation = zeit.content.text.interfaces.IValidationSchema(
            json_content)
        validation.schema_url = (
            'https://testschema.zeit.de/openapi.yaml')
        validation.field_name = 'evil'
        with mock.patch(
                'zeit.content.text.json.ValidationSchema._get') as schema:
            schema.return_value = (
                self.schema_json, RefResolver.from_schema(
                    self.schema_json))
            with self.assertRaises(
                    zeit.content.text.interfaces.SchemaValidationError):
                validation.validate()

    def test_get_schema_from_url(self):
        json_content = zeit.content.text.json.JSON()
        validation = zeit.content.text.interfaces.IValidationSchema(
            json_content)
        validation.schema_url = (
            'https://testschema.zeit.de/openapi.yaml')
        validation.field_name = 'uuid'

        with requests_mock.Mocker() as r_mock:
            r_mock.register_uri(
                'GET', 'https://testschema.zeit.de/openapi.yaml',
                text=yaml.safe_dump(self.schema_json))
            schema, ref_resolver = validation._get()

        self.assertEqual(self.schema_json, schema)
        self.assertEqual(self.schema_json, ref_resolver.referrer)

    def test_validate_data_against_schema(self):
        json_content = zeit.content.text.json.JSON()
        json_content.text = '"{urn:uuid:!noid!}"'
        validation = zeit.content.text.interfaces.IValidationSchema(
            json_content)
        validation.schema_url = (
            'https://testschema.zeit.de/openapi.yaml')
        validation.field_name = 'uuid'

        with mock.patch(
                'zeit.content.text.json.ValidationSchema._get') as schema:
            schema.return_value = (
                self.schema_json, RefResolver.from_schema(
                    self.schema_json))
            with self.assertRaises(
                    zeit.content.text.interfaces.SchemaValidationError):
                validation.validate()
            json_content.text = '"{urn:uuid:d995ba5a}"'
            validation.validate()

    def test_schema_reference_resolver_should_work(self):
        json_content = zeit.content.text.json.JSON()
        json_content.text = '["{urn:uuid:d995ba5a}"]'
        validation = zeit.content.text.interfaces.IValidationSchema(
            json_content)
        validation.schema_url = (
            'https://testschema.zeit.de/openapi.yaml')
        schema_json = {
            'components': {
                'schemas': {
                    'overlord': {
                        'type': 'array',
                        'items': {
                            '$ref': '#/components/schemas/uuid'
                        }
                    },
                    'uuid': {
                        'type': 'string',
                        'pattern':
                            "^((\\{urn:uuid:)?([a-f0-9]{8})\\}?)$"}}}}
        validation.field_name = 'overlord'
        with mock.patch(
                'zeit.content.text.json.ValidationSchema._get') as schema:
            schema.return_value = (
                schema_json, RefResolver.from_schema(schema_json))
            validation.validate()
