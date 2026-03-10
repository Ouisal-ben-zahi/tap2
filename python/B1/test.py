from docxtpl import DocxTemplate
import json

def generer_cv(json_data, template_path, output_path):
    doc = DocxTemplate(template_path)
    
    context = json.loads(json_data) if isinstance(json_data, str) else json_data

    def clean_data(obj):
        if isinstance(obj, dict):
            return {k: clean_data(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_data(i) for i in obj]
        elif isinstance(obj, str):
            return obj.strip() # Enlève les \n et les espaces en trop
        return obj

    context_propre = clean_data(context)
    
    doc.render(context_propre)
    doc.save(output_path)
    print(f"CV généré avec succès : {output_path}")

