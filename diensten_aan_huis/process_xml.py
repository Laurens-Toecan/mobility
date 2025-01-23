import azure.functions as func
import xmltodict
import json

def detect_language_langdetect(text:str) -> str:
    from langdetect import detect_langs
    language = detect_langs(text)
    return language[0].lang, language[0].prob

def detect_language_lingua(text:str) -> str:
    from lingua import Language, LanguageDetectorBuilder
    languages = {Language.DUTCH: 'nl', Language.ENGLISH: 'en', Language.FRENCH: 'fr', Language.GERMAN: 'de'}
    lang_dict = {k.name: v for k, v in languages.items()}
    detector = LanguageDetectorBuilder.from_languages(*languages).build()
    language = detector.detect_language_of(text)
    confidence = detector.compute_language_confidence(text, language)
    return lang_dict[language.name], confidence

def detect_language_langid(text:str) -> str:
    from py3langid.langid import LanguageIdentifier, MODEL_FILE
    identifier = LanguageIdentifier.from_pickled_model(MODEL_FILE, norm_probs=True)
    language, confidence = identifier.classify(text)
    return language, float(confidence)

def detect_language(text:str) -> str:
    language1, confidence1 = detect_language_langdetect(text)
    language2, confidence2 = detect_language_lingua(text)
    language3, confidence3 = detect_language_langid(text)
    confident = (
        ((confidence1 > 0.5) + (confidence2 > 0.5) + (confidence3 > 0.5)) >= 2
            and
        language1 == language2 == language3
    )
    language = language1 if confident else ''
    return language

def convert_xml_to_json(xml:str) -> dict:
    output = dict()

    parsed_data = xmltodict.parse(xml)
    assert 'File' in parsed_data, 'XML format unknown'

    for main_key, values in parsed_data['File'].items():
        if isinstance(values, str):
            output |= {main_key.lower(): values.lower() if values is not None else ''}
        elif isinstance(values, dict):
            output |= {f'{main_key}_{sub_key}'.lower(): value.lower() if value is not None else '' for sub_key, value in values.items()}

    output = {conversion_dict[key] if key in conversion_dict else key: value for key, value in output.items()}

    return output

def process_xml(xml:str) -> dict:
    data = convert_xml_to_json(xml)
    data['ai_language'] = detect_language(data['damage_description_long'])
    return data

conversion_dict = {
    'identificationclient_id': 'company_reference',
    'type': 'damage_type',
    'employee_companyid': 'company_id',
    'employee_companyname': 'company_name',
    'employee_companyabbreviation': 'company_abbreviation',
    'modifications_accident_location_description': 'damage_location',
    'modifications_damage_descriptionlong': 'damage_description_long',
    'modifications_damage_descriptionshort': 'damage_description_short',
    'modifications_damage_donebyemployee': 'damage_by_employee',
    'modifications_damage_pv': 'damage_pv',
    'modifications_damage_witness': 'damage_witness',
}

def main(req: func.HttpRequest) -> func.HttpResponse:
    print(req.params)
    xml = req.params.get('body')
    return func.HttpResponse(process_xml(xml))
